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
        """True if std < max(20% of max_score, 0.4) — adaptive threshold, floor raised to 0.4."""
        if not max_score:
            return None
        std = self._safe_stdev(scores)
        if std is None:
            return None
        return std < max(0.20 * max_score, 0.4)


    def pass_min_score(self, ruim_scores, max_score):
        """True if mean(ruim) < 35% of max_score."""
        mean = self._safe_mean(ruim_scores)
        if mean is None or not max_score:
            return None
        return mean < 0.35 * max_score


    def pass_med_score(self, med_scores, max_score, all_scores=None):
        """True if mean, median, or majority (≥2/3) of individual scores falls within [25%, 85%] of max_score.
        Special case: if all valid med scores equal max_score, return True only if at least one score
        among all 9 corrections (ruim+med+max) is neither 0 nor max_score — i.e., the corrector is
        capable of partial scoring. If every correction is binary (0 or max_score), return False."""
        if not max_score:
            return None
        valid = [s for s in med_scores if s is not None]
        if not valid:
            return None
        # Escape hatch: all med samples hit max_score
        if all(s == max_score for s in valid):
            if all_scores:
                all_valid = [s for s in all_scores if s is not None]
                if any(s != 0 and s != max_score for s in all_valid):
                    return True
            return False
        lo, hi = 0.25 * max_score, 0.85 * max_score
        mean = self._safe_mean(med_scores)
        if mean is not None and lo <= mean <= hi:
            return True
        median = self._safe_median(med_scores)
        if median is not None and lo <= median <= hi:
            return True
        # Majority: at least 2 out of 3 scores within range
        if sum(1 for s in valid if lo <= s <= hi) >= 2:
            return True
        return False


    def pass_max_score(self, max_scores, max_score):
        """True if mean(max) > 80% of max_score."""
        mean = self._safe_mean(max_scores)
        if mean is None or not max_score:
            return None
        return mean > 0.80 * max_score


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
            self.pass_med_score(med_scores, max_score,           # pass_med_score
                                ruim_scores + med_scores + max_scores),
            self.pass_max_score(max_scores, max_score),          # pass_max_score
            error_log or "",                                     # log_erro
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),       # created_at
        ]
