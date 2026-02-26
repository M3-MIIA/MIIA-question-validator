import os
import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

class Database:
    
    def __init__(self):
        self.db_host = os.environ.get("DB_HOST")
        self.db_port = os.environ.get("DB_PORT", "5432") # Puxa a porta 5432 como fallback se não achar
        self.db_name = os.environ.get("DB_NAME")
        self.db_user = os.environ.get("DB_USER")
        self.db_pass = os.environ.get("DB_PASSWORD")

        database_vars = [self.db_host, self.db_name, self.db_user, self.db_pass]
        if not all(database_vars):
            raise ValueError("ERROR: missing database configuration variables in .env file.")


    def connect(self):
        conn_info = f"host={self.db_host} port={self.db_port} dbname={self.db_name} user={self.db_user} password={self.db_pass}"
        return psycopg.connect(conn_info)


    def get_question_structure(self, integration_id):
        query = """
        SELECT
            q.id as question_id,
            q.statement as question_statement,
            q.type as question_type,
            i.name as item_name,
            i.max_score,
            i.starts_max,
            i.eval_mode as i_eval_mode,
            g.name as grouping_name,
            c.code as classification_code,
            c.short_description,
            c.long_description,
            cg.weight,
            cg.type,
            cg.eval_target,
            cg.rigor_level,
            cg.user_context,
            cg.eval_mode as cls_eval_mode
        FROM question q
        LEFT JOIN question_item qi ON q.id = qi.question_id
        LEFT JOIN item i ON qi.item_id = i.id
        LEFT JOIN item_grouping ig ON i.id = ig.item_id
        LEFT JOIN grouping g ON ig.grouping_id = g.id
        LEFT JOIN classification_grouping cg ON g.id = cg.grouping_id
        LEFT JOIN classification c ON cg.classification_id = c.id
        LEFT JOIN question_answer qa ON q.id = qa.question_id
        LEFT JOIN job j ON qa.job_id = j.id
        WHERE q.integration_id = %s::text
        GROUP BY q.id, q.integration_id, q.statement, q.type, i.id, i.name, i.max_score, i.starts_max, i.eval_mode,
                 g.id, g.name, c.id, c.code, c.short_description, c.long_description, cg.id, cg.weight, cg.type, cg.eval_target, cg.user_context, cg.eval_mode
        ORDER BY i.id, g.id, c.id;
        """

        try:
            with self.connect() as conn:
                # O row_factory converte a saída para dicionários
                with conn.cursor(row_factory=dict_row) as cur:
                    
                    # Passamos o integration_id como uma tupla (note a vírgula)
                    cur.execute(query, (integration_id,))
                    linhas = cur.fetchall()

                    print(f"Buscadas {cur.rowcount} linhas de critério para o integration_id {integration_id}.")

                    # Fail-Fast: Se a query não trouxer nada, retorna vazio
                    if not linhas:
                        return None

                    # Extrai os dados que são iguais para todas as linhas (pegamos da primeira linha [0])
                    dados_estruturados = {
                        "question_id": linhas[0]["question_id"],
                        "statement": linhas[0]["question_statement"],
                        "type": linhas[0]["question_type"],
                        "criteria": []
                    }

                    # Itera sobre todas as linhas para montar a estrutura tabular dos critérios
                    for linha in linhas:
                        criterio = {
                            "item_name": linha["item_name"],
                            "max_score": float(linha["max_score"]) if linha["max_score"] else None,
                            "grouping_name": linha["grouping_name"],
                            "classification_code": linha["classification_code"],
                            "short_description": linha["short_description"],
                            "long_description": linha["long_description"],
                            "user_context": linha["user_context"],
                            "weight": float(linha["weight"]) if linha["weight"] else None,
                            "type": linha["type"],
                            "eval_target": linha["eval_target"],
                            "eval_mode": linha["cls_eval_mode"],
                            "rigor_level": linha["rigor_level"],
                        }
                        dados_estruturados["criteria"].append(criterio)

                    return dados_estruturados

        except Exception as e:
            print(f"Erro no Banco de Dados: {e}")
            return None


    def ensure_tenant_question(self, integration_id):
        """
        Garante que o integration_id esteja vinculado ao tenant configurado em TENANT_ID.
        Retorna True se já existia, False se foi inserido, None em caso de erro.
        """
        tenant_id = int(os.environ.get("TENANT_ID", 11))

        check_query = """
            SELECT id FROM tenant_question
            WHERE tenant_id = %s AND integration_id = %s
        """
        get_question_id_query = """
            SELECT id FROM question WHERE integration_id = %s::text LIMIT 1
        """
        insert_query = """
            INSERT INTO tenant_question (tenant_id, question_id, integration_id, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (tenant_id, integration_id) DO NOTHING
        """

        try:
            with self.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(check_query, (tenant_id, integration_id))
                    if cur.fetchone():
                        return True  # já existe

                    cur.execute(get_question_id_query, (integration_id,))
                    row = cur.fetchone()
                    if not row:
                        print(f"[PRÉ-VALIDAÇÃO] integration_id '{integration_id}' não encontrado na tabela question. Pulando inserção.")
                        return None

                    question_id = row[0]
                    cur.execute(insert_query, (tenant_id, question_id, integration_id))
                    conn.commit()
                    print(f"[PRÉ-VALIDAÇÃO] Inserido tenant_question: tenant={tenant_id}, question_id={question_id}, integration_id={integration_id}")
                    return False

        except Exception as e:
            print(f"[PRÉ-VALIDAÇÃO] Erro ao garantir tenant_question para '{integration_id}': {e}")
            return None