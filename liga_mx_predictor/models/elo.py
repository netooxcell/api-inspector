"""
Sistema de rating ELO dinámico para Liga MX.

Metodología: variante del "World Football Elo Ratings" (eloratings.net),
usada ampliamente para fútbol de clubes:

  * Rating inicial: 1500 para cualquier equipo la primera vez que aparece.
  * Ventaja de local: se suma HOME_ADVANTAGE puntos al rating del local
    únicamente para calcular el resultado esperado (no se persiste).
  * Resultado esperado (Elo estándar):
        E_home = 1 / (1 + 10^(-(elo_home + HOME_ADV - elo_away) / 400))
  * Resultado real: 1 = victoria local, 0.5 = empate, 0 = victoria visitante.
  * Multiplicador por margen de victoria (MOV), fórmula de eloratings.net:
        mov_mult = ln(|goal_diff| + 1) * (2.2 / (elo_winner_diff * 0.001 + 2.2))
    donde elo_winner_diff es la diferencia de rating a favor del equipo que
    ganó (0 si empate). Esto castiga menos una goleada contra un rival mucho
    más débil, y premia más una goleada como equipo "chico" ante un rival
    fuerte.
  * Actualización: elo_new = elo_old + K * mov_mult * (resultado - esperado)

Todas las ratings devueltas por `compute_elo_history` son **pre-partido**
(el rating con el que el equipo llegó a ese partido, antes de conocer su
resultado) — de ahí que sean seguras de usar como features sin fuga de
información: para el partido en la fila N solo se usó información de partidos
1..N-1.

Uso típico:
    from models.elo import compute_elo_history
    matches, final_ratings = compute_elo_history(matches_df)
"""
import math

INITIAL_ELO = 1500.0
HOME_ADVANTAGE = 80.0
K_FACTOR = 20.0


def _expected_score(elo_a, elo_b):
    return 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / 400.0))


def _mov_multiplier(goal_diff, elo_diff_winner):
    goal_diff = abs(goal_diff)
    if goal_diff == 0:
        return 1.0
    return math.log(goal_diff + 1) * (2.2 / (elo_diff_winner * 0.001 + 2.2))


def compute_elo_history(matches_df):
    """
    matches_df: DataFrame ordenado o no, con columnas date, home_team,
    away_team, home_goals, away_goals. Se ordena internamente por fecha para
    garantizar actualización cronológica correcta.

    Devuelve:
      matches_out: copia de matches_df (ordenada por fecha) con columnas
                   nuevas home_elo_pre, away_elo_pre, elo_diff_pre.
      final_ratings: dict {equipo_normalizado: rating_elo_actual} tras
                     procesar el último partido disponible — se usa para
                     generar features de partidos futuros (fixtures).
    """
    df = matches_df.sort_values("date").reset_index(drop=True).copy()
    ratings = {}
    home_elo_pre = []
    away_elo_pre = []

    for _, row in df.iterrows():
        home, away = row["home_team"], row["away_team"]
        elo_home = ratings.get(home, INITIAL_ELO)
        elo_away = ratings.get(away, INITIAL_ELO)

        home_elo_pre.append(elo_home)
        away_elo_pre.append(elo_away)

        hg, ag = row["home_goals"], row["away_goals"]
        if hg > ag:
            result_home = 1.0
        elif hg == ag:
            result_home = 0.5
        else:
            result_home = 0.0

        expected_home = _expected_score(elo_home + HOME_ADVANTAGE, elo_away)

        goal_diff = hg - ag
        if hg > ag:
            elo_diff_winner = (elo_home + HOME_ADVANTAGE) - elo_away
        elif ag > hg:
            elo_diff_winner = elo_away - (elo_home + HOME_ADVANTAGE)
        else:
            elo_diff_winner = 0.0
        mult = _mov_multiplier(goal_diff, max(elo_diff_winner, 0.0))

        delta = K_FACTOR * mult * (result_home - expected_home)
        ratings[home] = elo_home + delta
        ratings[away] = elo_away - delta

    df["home_elo_pre"] = home_elo_pre
    df["away_elo_pre"] = away_elo_pre
    df["elo_diff_pre"] = df["home_elo_pre"] - df["away_elo_pre"]

    return df, ratings


def elo_win_draw_loss_probs(elo_home, elo_away, home_advantage=HOME_ADVANTAGE):
    """
    Aproximación de probabilidades 1X2 a partir de la diferencia de Elo,
    usada como feature adicional / sanity check frente a los modelos ML y
    Poisson (no reemplaza su salida).
    """
    expected_home = _expected_score(elo_home + home_advantage, elo_away)
    # Reparto empate/decisión basado en la curva empírica de eloratings.net:
    # a diferencia de Elo pequeña, mayor probabilidad de empate.
    diff = (elo_home + home_advantage) - elo_away
    draw_prob = max(0.18, 0.30 - abs(diff) / 1200)
    home_win = expected_home * (1 - draw_prob) + (expected_home - 0.5) * draw_prob * 0.3
    home_win = min(max(home_win, 0.02), 0.96)
    away_win = 1 - draw_prob - home_win
    if away_win < 0.02:
        away_win = 0.02
        home_win = 1 - draw_prob - away_win
    return home_win, draw_prob, away_win
