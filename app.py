import itertools
import re
from itertools import combinations

import requests
import streamlit as st

LOTOFACIL_TOTAL = 15
LOTOFACIL_MIN = 1
LOTOFACIL_MAX = 25
API_URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil/latest"


def parse_numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", text)]


def format_game(numbers: list[int]) -> str:
    return ",".join(f"{n:02d}" for n in sorted(numbers))


def parse_game_line(line: str) -> list[int] | None:
    line = line.strip()
    if not line:
        return None
    numbers = parse_numbers(line)
    if not numbers:
        return None
    return sorted(set(numbers))


def generate_combinations(fixed: list[int], groups: list[tuple[list[int], int]]) -> list[list[int]]:
    group_combos = []
    for numbers, pick in groups:
        unique = sorted(set(numbers))
        if pick > len(unique):
            raise ValueError(
                f"Grupo {numbers}: escolher {pick} dezenas, mas só há {len(unique)} disponíveis."
            )
        group_combos.append(list(combinations(unique, pick)))

    games = []
    for picks in itertools.product(*group_combos):
        game = sorted(set(fixed + [n for group in picks for n in group]))
        if len(game) == LOTOFACIL_TOTAL:
            games.append(game)
    return games


def validate_numbers(numbers: list[int], label: str) -> list[str]:
    errors = []
    for n in numbers:
        if n < LOTOFACIL_MIN or n > LOTOFACIL_MAX:
            errors.append(f"{label}: dezena {n} fora do intervalo ({LOTOFACIL_MIN}-{LOTOFACIL_MAX}).")
    if len(numbers) != len(set(numbers)):
        errors.append(f"{label}: há dezenas repetidas.")
    return errors


def fetch_latest_result() -> dict:
    response = requests.get(API_URL, timeout=15)
    response.raise_for_status()
    return response.json()


def count_hits(game: list[int], drawn: set[int]) -> int:
    return len(set(game) & drawn)


def render_generator():
    st.subheader("Gerador de Combinações")
    st.caption(
        "Informe as dezenas fixas (presentes em todos os jogos) e os grupos variáveis "
        f"(dezenas + quantidade a escolher). Cada jogo deve ter {LOTOFACIL_TOTAL} dezenas."
    )

    fixed_text = st.text_input(
        "Dezenas fixas",
        placeholder="Ex: 01, 05, 10, 15, 20",
        help="Dezenas que entram em todos os jogos gerados.",
    )

    st.markdown("**Grupos variáveis**")
    num_groups = st.number_input("Quantidade de grupos", min_value=0, max_value=10, value=2, step=1)

    groups = []
    for i in range(int(num_groups)):
        col1, col2 = st.columns([3, 1])
        with col1:
            group_text = st.text_input(
                f"Grupo {i + 1} — dezenas",
                key=f"group_nums_{i}",
                placeholder="Ex: 02, 03, 04, 06, 07",
            )
        with col2:
            pick = st.number_input(
                f"Escolher",
                min_value=1,
                max_value=LOTOFACIL_TOTAL,
                value=1,
                key=f"group_pick_{i}",
            )
        if group_text.strip():
            groups.append((parse_numbers(group_text), int(pick)))

    if st.button("Gerar combinações", type="primary"):
        fixed = parse_numbers(fixed_text)
        errors = validate_numbers(fixed, "Dezenas fixas")

        total_picks = len(fixed) + sum(pick for _, pick in groups)
        if total_picks != LOTOFACIL_TOTAL:
            errors.append(
                f"Total de dezenas deve ser {LOTOFACIL_TOTAL} "
                f"(fixas + escolhas dos grupos). Atual: {total_picks}."
            )

        all_used = fixed[:]
        for idx, (nums, pick) in enumerate(groups, start=1):
            errors.extend(validate_numbers(nums, f"Grupo {idx}"))
            all_used.extend(nums)

        if len(all_used) != len(set(all_used)):
            errors.append("Há dezenas repetidas entre fixas e grupos.")

        if errors:
            for err in errors:
                st.error(err)
            return

        try:
            games = generate_combinations(fixed, groups)
        except ValueError as exc:
            st.error(str(exc))
            return

        if not games:
            st.warning("Nenhuma combinação válida encontrada.")
            return

        st.session_state["generated_games"] = games
        st.success(f"{len(games):,} combinação(ões) gerada(s)!".replace(",", "."))

    if "generated_games" in st.session_state:
        games = st.session_state["generated_games"]
        st.info(f"**{len(games):,}** jogos prontos para download.".replace(",", "."))

        preview = min(10, len(games))
        st.markdown(f"**Prévia** (primeiros {preview} jogos):")
        for game in games[:preview]:
            st.text(format_game(game))

        txt_content = "\n".join(format_game(g) for g in games)
        st.download_button(
            label="Baixar jogos (.txt)",
            data=txt_content,
            file_name="jogos_lotofacil.txt",
            mime="text/plain",
        )


def render_checker():
    st.subheader("Conferidor")
    st.caption("Busca o último resultado da Lotofácil e confere seus jogos.")

    if st.button("Buscar último concurso"):
        with st.spinner("Consultando API..."):
            try:
                st.session_state["latest_result"] = fetch_latest_result()
            except requests.RequestException as exc:
                st.error(f"Erro ao buscar resultado: {exc}")
                return

    result = st.session_state.get("latest_result")
    if result:
        drawn = sorted(int(d) for d in result["dezenas"])
        st.markdown(
            f"**Concurso {result['concurso']}** — {result['data']}  \n"
            f"Dezenas sorteadas: **{', '.join(f'{d:02d}' for d in drawn)}**"
        )

    st.markdown("**Seus jogos**")
    input_method = st.radio("Como enviar os jogos?", ["Colar texto", "Enviar arquivo .txt"], horizontal=True)

    games_text = ""
    if input_method == "Colar texto":
        games_text = st.text_area(
            "Cole os jogos (um por linha)",
            height=200,
            placeholder="01,02,03,04,05,06,07,08,09,10,11,12,13,14,15",
        )
    else:
        uploaded = st.file_uploader("Arquivo .txt", type=["txt"])
        if uploaded:
            games_text = uploaded.read().decode("utf-8")

    if st.button("Conferir jogos", type="primary"):
        if not result:
            st.warning("Busque o último concurso antes de conferir.")
            return

        drawn_set = set(int(d) for d in result["dezenas"])
        lines = games_text.strip().splitlines()
        if not lines:
            st.warning("Nenhum jogo informado.")
            return

        results = []
        invalid_lines = []
        for idx, line in enumerate(lines, start=1):
            game = parse_game_line(line)
            if game is None:
                continue
            if len(game) != LOTOFACIL_TOTAL:
                invalid_lines.append(f"Linha {idx}: {len(game)} dezenas (esperado {LOTOFACIL_TOTAL}).")
                continue
            hits = count_hits(game, drawn_set)
            results.append({"Jogo": format_game(game), "Acertos": hits})

        if invalid_lines:
            for msg in invalid_lines:
                st.warning(msg)

        if not results:
            st.warning("Nenhum jogo válido para conferir.")
            return

        st.markdown(f"**{len(results)}** jogo(s) conferido(s)")

        summary = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0, "outros": 0}
        for r in results:
            h = r["Acertos"]
            if h in summary:
                summary[h] += 1
            else:
                summary["outros"] += 1

        cols = st.columns(5)
        for i, col in enumerate(cols):
            pts = 11 + i
            col.metric(f"{pts} pts", summary[pts])

        if summary["outros"]:
            st.caption(f"Jogos com menos de 11 acertos: {summary['outros']}")

        winners = [r for r in results if r["Acertos"] >= 11]
        if winners:
            st.markdown("**Jogos premiados (11+ acertos)**")
            st.dataframe(winners, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum jogo com 11 ou mais acertos.")

        st.markdown("**Todos os jogos**")
        st.dataframe(results, use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title="Lotofácil — Gerador & Conferidor", page_icon="🎱", layout="wide")
    st.title("Lotofácil")
    st.markdown("Gerador de combinações e conferidor de jogos.")

    tab_gerador, tab_conferidor = st.tabs(["Gerador de Combinações", "Conferidor"])

    with tab_gerador:
        render_generator()

    with tab_conferidor:
        render_checker()


if __name__ == "__main__":
    main()
