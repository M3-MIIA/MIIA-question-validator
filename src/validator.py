import statistics
from datetime import datetime


class Validator:

    def _safe_mean(self, scores):
        valid = [s for s in scores if s is not None]
        return statistics.mean(valid) if valid else None

   
    def _safe_median(self, scores):
        valid = [s for s in scores if s is not None]
        return statistics.median(valid) if valid else None


    def _safe_stdev(self, scores):
        valid = [s for s in scores if s is not None]
        return statistics.stdev(valid) if len(valid) >= 2 else None


    def pass_bolo(self, bolo_score):
        if bolo_score is None:
            return None
        return bolo_score == 0


    def pass_var(self, scores, max_score):
        """True if std / max_score < 0.20 (variation < 20% of the question's max score)."""
        if not max_score:
            return None
        std = self._safe_stdev(scores)
        if std is None:
            return None
        return (std / max_score) < 0.20


    def pass_min_score(self, ruim_scores, max_score):
        """True if median(ruim) < 35% of max_score."""
        median = self._safe_median(ruim_scores)
        if median is None or not max_score:
            return None
        return median < 0.35 * max_score


    def pass_med_score(self, med_scores, max_score):
        """True if 35% <= median(med) <= 75% of max_score."""
        median = self._safe_median(med_scores)
        if median is None or not max_score:
            return None
        return 0.35 * max_score <= median <= 0.75 * max_score


    def pass_max_score(self, max_scores, max_score):
        """True if median(max) > 75% of max_score."""
        median = self._safe_median(max_scores)
        if median is None or not max_score:
            return None
        return median > 0.75 * max_score


    def build_row(self, question_id, integration_id, bolo_score,
                  ruim_scores, med_scores, max_scores, max_score, error_log=None):
        return [
            question_id,                                         # question_id DEV
            integration_id,                                      # Questão (integration_id)
            bolo_score,                                          # Receita de Bolo
            *ruim_scores,                                        # Ruim 1, Ruim 2, Ruim 3
            *med_scores,                                         # Med 1, Med 2, Med 3
            *max_scores,                                         # Max 1, Max 2, Max 3
            max_score,                                           # Max Score
            "",                                                  # question_id PRD
            "",                                                  # validada_por
            self.pass_bolo(bolo_score),                          # pass_bolo
            self.pass_var(ruim_scores, max_score),               # pass_ruim_var
            self.pass_var(med_scores,  max_score),               # pass_med_var
            self.pass_var(max_scores,  max_score),               # pass_max_var
            self.pass_min_score(ruim_scores, max_score),         # pass_min_score
            self.pass_med_score(med_scores, max_score),          # pass_med_score
            self.pass_max_score(max_scores, max_score),          # pass_max_score
            error_log or "",                                     # log_erro
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),       # created_at
        ]
