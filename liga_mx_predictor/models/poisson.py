"""
Modelo de goles de Poisson con fuerza de ataque/defensa por equipo
(modelo de Maher, base del modelo de Dixon-Coles).

Se entrena con partidos ANTERIORES a la fecha de corte (walk-forward friendly:
recibe ya el subconjunto de entrenamiento, no hace su propio split temporal).

Estructura larga: cada partido aporta 2 observaciones de conteo de goles:
  (equipo=local, oponente=visitante, es_local=1, goles=home_goals)
  (equipo=visitante, oponente=local, es_local=0, goles=away_goals)

Se ajusta un GLM Poisson:
    goles ~ C(equipo) + C(oponente) + es_local

El coeficiente de C(equipo) aproxima la fuerza de ataque, el de C(oponente)
la fuerza de defensa (con signo invertido: coeficiente alto = defensa
débil, permite más goles al rival), y es_local captura la ventaja de jugar
en casa a nivel de goles.

Se añade una corrección de Dixon-Coles (parámetro rho) para los marcadores
bajos (0-0, 1-0, 0-1, 1-1), donde el supuesto de independencia entre goles
del local y visitante se ajusta empíricamente peor.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

MAX_GOALS = 8


def _long_format_for_poisson(matches):
    home = pd.DataFrame({
        "team": matches["home_team"], "opponent": matches["away_team"],
        "is_home": 1, "goals": matches["home_goals"],
    })
    away = pd.DataFrame({
        "team": matches["away_team"], "opponent": matches["home_team"],
        "is_home": 0, "goals": matches["away_goals"],
    })
    return pd.concat([home, away], ignore_index=True)


def fit_poisson_model(train_matches):
    """
    train_matches: DataFrame de partidos jugados con home_team, away_team,
    home_goals, away_goals. Debe contener SOLO partidos anteriores a la fecha
    que se quiere predecir (walk-forward / backtest lo garantiza).
    """
    long_df = _long_format_for_poisson(train_matches)
    model = smf.glm(
        formula="goals ~ C(team) + C(opponent) + is_home",
        data=long_df, family=sm.families.Poisson()
    ).fit()
    known_teams = set(train_matches["home_team"]) | set(train_matches["away_team"])
    league_avg_goals = long_df["goals"].mean()
    return {"model": model, "known_teams": known_teams, "league_avg_goals": league_avg_goals}


def expected_goals(fitted, home_team, away_team):
    """
    Devuelve (lambda_home, lambda_away). Si un equipo no fue visto en
    entrenamiento (debut / datos insuficientes), se usa el promedio de goles
    de la liga como respaldo neutro en vez de fallar o inventar un valor
    arbitrario.
    """
    model, known = fitted["model"], fitted["known_teams"]
    if home_team not in known or away_team not in known:
        avg = fitted["league_avg_goals"]
        return avg, avg

    row_home = pd.DataFrame({"team": [home_team], "opponent": [away_team], "is_home": [1]})
    row_away = pd.DataFrame({"team": [away_team], "opponent": [home_team], "is_home": [0]})
    lam_home = float(model.predict(row_home).iloc[0])
    lam_away = float(model.predict(row_away).iloc[0])
    return lam_home, lam_away


def _dc_tau(x, y, lam_home, lam_away, rho):
    """Corrección de Dixon-Coles (1997) para dependencia en marcadores bajos."""
    if x == 0 and y == 0:
        return 1 - lam_home * lam_away * rho
    if x == 0 and y == 1:
        return 1 + lam_home * rho
    if x == 1 and y == 0:
        return 1 + lam_away * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


def score_matrix(lam_home, lam_away, max_goals=MAX_GOALS, rho=-0.05):
    """
    Matriz P(home_goals=i, away_goals=j) para i,j en [0, max_goals], con
    corrección de Dixon-Coles en los marcadores bajos. rho negativo (valor
    típico en la literatura, entre -0.1 y 0) reduce ligeramente la
    probabilidad de 0-0/1-1 y ajusta 1-0/0-1 frente al supuesto de Poisson
    independiente puro.
    """
    from scipy.stats import poisson
    i = np.arange(0, max_goals + 1)
    p_home = poisson.pmf(i, lam_home)
    p_away = poisson.pmf(i, lam_away)
    matrix = np.outer(p_home, p_away)
    for x in range(2):
        for y in range(2):
            matrix[x, y] *= _dc_tau(x, y, lam_home, lam_away, rho)
    matrix = matrix / matrix.sum()  # renormalize after DC correction
    return matrix


def outcome_probabilities(matrix):
    home_win = np.tril(matrix, -1).sum()
    draw = np.trace(matrix)
    away_win = np.triu(matrix, 1).sum()
    return home_win, draw, away_win


def goal_market_probabilities(matrix):
    max_goals = matrix.shape[0] - 1
    total_goals_probs = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            total_goals_probs[i + j] = total_goals_probs.get(i + j, 0.0) + matrix[i, j]

    over_1_5 = sum(p for g, p in total_goals_probs.items() if g > 1.5)
    over_2_5 = sum(p for g, p in total_goals_probs.items() if g > 2.5)
    under_2_5 = 1 - over_2_5
    btts = 1 - matrix[0, :].sum() - matrix[:, 0].sum() + matrix[0, 0]

    flat_idx = np.dstack(np.unravel_index(np.argsort(-matrix, axis=None), matrix.shape))[0]
    most_likely = tuple(int(v) for v in flat_idx[0])

    return {
        "over_1_5": over_1_5, "over_2_5": over_2_5, "under_2_5": under_2_5,
        "btts": btts, "most_likely_score": most_likely,
    }


def predict_match(fitted, home_team, away_team, max_goals=MAX_GOALS, rho=-0.05):
    lam_home, lam_away = expected_goals(fitted, home_team, away_team)
    matrix = score_matrix(lam_home, lam_away, max_goals, rho)
    home_win, draw, away_win = outcome_probabilities(matrix)
    markets = goal_market_probabilities(matrix)
    return {
        "lambda_home": lam_home, "lambda_away": lam_away,
        "home_win": home_win, "draw": draw, "away_win": away_win,
        "score_matrix": matrix, **markets,
    }
