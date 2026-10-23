# itertools importa utilitarios para combinar grupos e percorrer produtos cartesianos.
import itertools
# csv escreve os resultados completos da conferencia em um arquivo CSV.
import csv
# ThreadPoolExecutor consulta concursos historicos simultaneamente.
from concurrent.futures import ThreadPoolExecutor
# base64 codifica a previa PDF para exibi-la em um quadro incorporado.
import base64
# math importa operacoes matematicas como combinacoes e teto de paginas.
import math
# re importa expressoes regulares para localizar dezenas em textos.
import re
# io importa buffers em memoria usados para imagens, texto CSV e arquivos PDF.
from io import BytesIO, StringIO
# datetime importa tipos e funcoes para lidar com datas de concursos.
from datetime import date, datetime, timedelta
# itertools importa utilitarios para combinar grupos e percorrer produtos cartesianos.
from itertools import combinations
# pathlib importa caminhos de arquivo independentes do sistema operacional.
from pathlib import Path
# local guarda uma sessao HTTP separada para cada thread de consulta.
from threading import local

# requests importa o cliente HTTP usado para consultar os resultados da API.
import requests
# HTTPAdapter instala repeticoes automaticas nas conexoes HTTP.
from requests.adapters import HTTPAdapter
# Retry configura tentativas com espera progressiva para falhas transitórias.
from urllib3.util.retry import Retry
# streamlit importa a biblioteca que renderiza a interface web do aplicativo.
import streamlit as st
# PIL importa ferramentas de leitura e conversao de imagens.
from PIL import Image
# reportlab.lib.pagesizes fornece os recursos usados pelo aplicativo.
from reportlab.lib.pagesizes import A4
# reportlab.lib.utils fornece os recursos usados pelo aplicativo.
from reportlab.lib.utils import ImageReader
# reportlab.pdfgen fornece os recursos usados pelo aplicativo.
from reportlab.pdfgen import canvas

# LOTOFACIL_MIN define a menor dezena valida da Lotofacil.
LOTOFACIL_MIN = 1
# LOTOFACIL_MAX define a maior dezena valida da Lotofacil.
LOTOFACIL_MAX = 25
# ALL_NUMBERS guarda a lista de dezenas validas entre os limites configurados.
ALL_NUMBERS = list(range(LOTOFACIL_MIN, LOTOFACIL_MAX + 1))
# MAX_GENERATED_GAMES limita a quantidade de combinacoes materializadas na memoria.
MAX_GENERATED_GAMES = 50_000
# GROUP_RANGES define os cinco grupos fixos do gerador por grupos.
GROUP_RANGES = tuple(tuple(range(start, start + 5)) for start in range(1, 26, 5))
# GROUP_DEFAULT_PICKS reproduz as quantidades iniciais da planilha enviada.
GROUP_DEFAULT_PICKS = (1, 4, 3, 4, 3)
# GROUP_DEFAULT_SELECTED_NUMBERS inicia o primeiro grupo apenas com 03 e os demais completos.
GROUP_DEFAULT_SELECTED_NUMBERS = {3, *range(6, 26)}
# API_URL aponta diretamente para o endpoint oficial de resultados da CAIXA.
API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
# API_CONTEST_URL monta o endereco oficial para um concurso especifico.
API_CONTEST_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{contest}"
# API_THREAD_LOCAL mantem conexoes HTTP independentes nas consultas paralelas.
API_THREAD_LOCAL = local()

# Tabela vigente da aposta da Lotofácil (CAIXA). Uma aposta com mais de 15
# dezenas equivale a várias apostas simples e por isso tem preço próprio.
# BET_PRICES mapeia a quantidade de dezenas de uma aposta ao seu preco informado.
BET_PRICES = {15: 3.50, 16: 56.00, 17: 476.00, 18: 2856.00, 19: 13566.00, 20: 54264.00}

# Guarda as regras CSS que controlam a aparencia e o layout responsivo da interface.
# CSS_PATH aponta para a folha de estilos externa compartilhada pelo aplicativo.
CSS_PATH = Path(__file__).parent / "static" / "styles.css"
# MODERN_CSS le os estilos externos para injecao unica na interface principal.
MODERN_CSS = f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>"


# Extrai todas as sequencias numericas do texto e converte cada uma em inteiro.
def parse_numbers(text: str) -> list[int]:
    # Devolve [int(n) for n in re.findall(r"\d+", text)] ao codigo que chamou esta funcao.
    return [int(n) for n in re.findall(r"\d+", text)]


# Formata as dezenas com dois digitos e virgulas para exportar ou exibir uma aposta.
def format_game(numbers: list[int]) -> str:
    # Devolve ",".join(f"{n:02d}" for n in numbers) ao codigo que chamou esta funcao.
    return ",".join(f"{n:02d}" for n in numbers)


# Remove um prefixo de identificacao como "Jogo 1:" antes de interpretar dezenas.
def strip_game_label(line: str) -> str:
    # Retira o rotulo inicial sem alterar numeros pertencentes ao jogo.
    return re.sub(r"^\s*jogo\s+\d+\s*[:.)-]\s*", "", line.strip(), flags=re.IGNORECASE)


# Interpreta uma linha como aposta e devolve dezenas unicas ordenadas, ou None se estiver vazia.
def parse_game_line(line: str) -> list[int] | None:
    # Limpa espacos e um eventual rotulo para evitar ler o indice como dezena.
    line = strip_game_label(line)
    # Verifica se `not line`.
    if not line:
        # Devolve None ao codigo que chamou esta funcao.
        return None
    # numbers recebe o valor que armazena em `numbers` o valor obtido de `parse_numbers(line)`.
    numbers = parse_numbers(line)
    # Verifica se `not numbers`.
    if not numbers:
        # Devolve None ao codigo que chamou esta funcao.
        return None
    # Localiza valores fora do intervalo oficial da Lotofacil.
    invalid_numbers = sorted({number for number in numbers if number not in ALL_NUMBERS})
    # Rejeita a aposta para evitar conferir dezenas inexistentes silenciosamente.
    if invalid_numbers:
        # Interrompe a leitura informando as dezenas invalidas encontradas.
        raise ValueError("Dezenas fora de 01 a 25: " + ", ".join(f"{number:02d}" for number in invalid_numbers))
    # Devolve sorted(set(numbers)) ao codigo que chamou esta funcao.
    return sorted(set(numbers))


# Inicializa ou normaliza a selecao de dezenas guardada no estado da sessao.
def init_selection(key: str) -> None:
    # Verifica se `key not in st.session_state`.
    if key not in st.session_state:
        # st.session_state[key] recebe o valor que monta a colecao de valores usada pela etapa atual.
        st.session_state[key] = []
    # Verifica a proxima condicao: `isinstance(st.session_state[key], set)`.
    elif isinstance(st.session_state[key], set):
        # st.session_state[key] recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
        st.session_state[key] = sorted(st.session_state[key])


# Consulta a ordem em que uma selecao foi criada para preservar a prioridade do usuario.
def selection_priority(key: str) -> int | None:
    # Devolve st.session_state.get("selection_priorities", {}).get(key) ao codigo que chamou esta funcao.
    return st.session_state.get("selection_priorities", {}).get(key)


# Alterna a presenca de uma dezena na selecao e registra sua ordem de escolha.
def toggle_number(key: str, num: int) -> None:
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    init_selection(key)
    # Verifica se `num in st.session_state[key]`.
    if num in st.session_state[key]:
        # Chama `st.session_state[key].remove` para executa a operacao do objeto com os argumentos indicados.
        st.session_state[key].remove(num)
        # Verifica se `not st.session_state[key]`.
        if not st.session_state[key]:
            # Chama `st.session_state.get` para consulta o estado da sessao sem exigir que a chave exista.
            st.session_state.get("selection_priorities", {}).pop(key, None)
    # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
    else:
        # Verifica se `not st.session_state[key]`.
        if not st.session_state[key]:
            # priorities recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
            priorities = st.session_state.setdefault("selection_priorities", {})
            # priorities[key] recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
            priorities[key] = st.session_state.get("selection_priority_counter", 0)
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            st.session_state["selection_priority_counter"] = priorities[key] + 1
        # Chama `st.session_state[key].append` para executa a operacao do objeto com os argumentos indicados.
        st.session_state[key].append(num)


# Retorna uma copia normalizada da selecao atual para evitar alteracoes acidentais do estado.
def get_selection(key: str) -> list[int]:
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    init_selection(key)
    # Devolve st.session_state[key].copy() ao codigo que chamou esta funcao.
    return st.session_state[key].copy()


# Remove dezenas repetidas mantendo a primeira ordem em que cada uma apareceu.
def unique_in_selection_order(numbers: list[int]) -> list[int]:
    """Remove duplicatas preservando a ordem em que as dezenas foram selecionadas."""
    # Devolve list(dict.fromkeys(numbers)) ao codigo que chamou esta funcao.
    return list(dict.fromkeys(numbers))


# Verifica se a aposta contem uma sequencia consecutiva do tamanho configurado.
def has_consecutive_sequence(game: list[int], max_sequence: int) -> bool:
    # Uma aposta vazia nao contem sequencias, mesmo se o limite for zero ou um.
    if not game:
        # Devolve False para uma entrada sem dezenas.
        return False
    # Qualquer aposta nao vazia contem uma sequencia de tamanho um.
    if max_sequence == 1:
        # Devolve True porque uma dezena isolada satisfaz o limite unitario.
        return True
    # Um limite nulo ou negativo nao representa um filtro de sequencias.
    if max_sequence <= 0:
        # Devolve False para indicar que nao ha uma sequencia a testar.
        return False
    # game_sorted recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
    game_sorted = sorted(game)
    # consecutive recebe o valor que armazena em `consecutive` o valor obtido de `1`.
    consecutive = 1
    # Percorre i in range(1, len(game_sorted)) e executa o bloco para cada item.
    for i in range(1, len(game_sorted)):
        # Verifica se `game_sorted[i] == game_sorted[i - 1] + 1`.
        if game_sorted[i] == game_sorted[i - 1] + 1:
            # Atualiza `consecutive` com o resultado da operacao `+=` aplicada a `1`.
            consecutive += 1
            # Verifica se `consecutive >= max_sequence`.
            if consecutive >= max_sequence:
                # Devolve True ao codigo que chamou esta funcao.
                return True
        # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
        else:
            # consecutive recebe o valor que armazena em `consecutive` o valor obtido de `1`.
            consecutive = 1
    # Devolve False ao codigo que chamou esta funcao.
    return False


# Retem apenas os jogos que atendem ao limite configurado de dezenas consecutivas.
def filter_games_by_sequence(games: list[list[int]], max_sequence: int, fixed: list[int] = None) -> list[list[int]]:
    # Verifica se `max_sequence == 0`.
    if max_sequence == 0:
        # Devolve games ao codigo que chamou esta funcao.
        return games
    
    # fixed_set recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
    fixed_set = set(fixed) if fixed else set()
    # filtered_games recebe o valor que monta a colecao de valores usada pela etapa atual.
    filtered_games = []
    # Percorre game in games e executa o bloco para cada item.
    for game in games:
        # variables_only recebe o valor que monta a colecao de valores usada pela etapa atual.
        variables_only = [num for num in game if num not in fixed_set]
        # Verifica se `not has_consecutive_sequence(variables_only, max_sequence)`.
        if not has_consecutive_sequence(variables_only, max_sequence):
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            filtered_games.append(game)
    # Devolve filtered_games ao codigo que chamou esta funcao.
    return filtered_games


# Renderiza um seletor visual simples de dezenas e devolve as dezenas marcadas.
def render_number_selector(key: str, label: str) -> list[int]:
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    init_selection(key)
    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown(f"**{label}**")

    # side_left, ticket_column, side_right recebe o valor que cria as colunas da interface usadas para organizar os controles.
    side_left, ticket_column, side_right = st.columns([0.2, 3.6, 0.2])
    # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
    with ticket_column:
        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown(
            """
            <div class="ticket-card">
                <div class="ticket-header">
                    <div class="ticket-header-title">LOTOFÁCIL</div>
                    <div class="ticket-header-sub">SELEÇÃO DE DEZENAS</div>
                </div>
                <div class="ticket-body">
            """,  # Fecha o fragmento HTML e o entrega ? chamada que o renderiza.
            # unsafe_allow_html recebe o valor que armazena em `unsafe_allow_html` o valor obtido de `True,`.
            unsafe_allow_html=True,
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

        # Percorre row in range(5) e executa o bloco para cada item.
        for row in range(5):
            # cols recebe o valor que cria as colunas da interface usadas para organizar os controles.
            cols = st.columns(5, gap="small")
            # Percorre col_idx in range(5) e executa o bloco para cada item.
            for col_idx in range(5):
                # num recebe o valor que armazena em `num` o valor obtido de `col_idx * 5 + row + 1`.
                num = col_idx * 5 + row + 1
                # is_selected recebe o valor que armazena em `is_selected` o valor obtido de `num in st.session_state[key]`.
                is_selected = num in st.session_state[key]
                # state_suffix recebe o valor que define o texto ou identificador `"selected" if is_selected else "empty"` usado nesta etapa.
                state_suffix = "selected" if is_selected else "empty"
                # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
                with cols[col_idx]:
                    # Verifica se `st.button(`.
                    if st.button(
                        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                        f"{num:02d}",
                        # key recebe o valor que define o texto ou identificador `f"btn_sel_{key}_{num}_{state_suffix}",` usado nesta etapa.
                        key=f"btn_sel_{key}_{num}_{state_suffix}",
                        # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
                        use_container_width=True,
                    # Inicia o bloco correspondente a estrutura de controle definida nesta linha.
                    ):
                        # Compoe a expressao ou os argumentos da operacao iniciada acima.
                        toggle_number(key, num)
                        # Chama `st.rerun` para solicita uma nova renderizacao da interface.
                        st.rerun()

        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown(
            """
                </div>
                <div class="ticket-legend">
                    <span class="legend-item"><span class="legend-dot dot-extra"></span> Selecionada</span>
                    <span class="legend-item"><span class="legend-dot dot-empty"></span> Livre</span>
                </div>
            </div>
            """,  # Fecha o fragmento HTML e o entrega ? chamada que o renderiza.
            # unsafe_allow_html recebe o valor que armazena em `unsafe_allow_html` o valor obtido de `True,`.
            unsafe_allow_html=True,
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

    # selected recebe o valor que armazena em `selected` o valor obtido de `get_selection(key)`.
    selected = get_selection(key)
    # Verifica se `selected`.
    if selected:
        # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
        st.caption(f"Selecionadas ({len(selected)}): {', '.join(f'{n:02d}' for n in selected)}")
    # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
    else:
        # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
        st.caption("Nenhuma dezena selecionada.")
    # Devolve selected ao codigo que chamou esta funcao.
    return selected


# Recupera dezenas fixas, variaveis e a ordem de cliques do volante interativo.
def ticket_state(key: str) -> tuple[list[int], list[int], dict[int, int]]:
    """Retorna fixas, variáveis e a ordem global dos cliques ativos."""
    # states recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    states = st.session_state.setdefault(f"{key}_states", {})
    # order recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    order = st.session_state.setdefault(f"{key}_order", {})
    # fixed recebe o valor que monta a colecao de valores usada pela etapa atual.
    fixed = [number for number in ALL_NUMBERS if states.get(number) == 1]
    # variables recebe o valor que monta a colecao de valores usada pela etapa atual.
    variables = [number for number in ALL_NUMBERS if states.get(number) == 2]
    # fixed.sort(key recebe o valor que armazena em `sort(key` o valor obtido de `lambda number: order[number])`.
    fixed.sort(key=lambda number: order[number])
    # variables.sort(key recebe o valor que armazena em `sort(key` o valor obtido de `lambda number: order[number])`.
    variables.sort(key=lambda number: order[number])
    # Devolve fixed, variables, order ao codigo que chamou esta funcao.
    return fixed, variables, order


# Avanca uma dezena entre os estados desmarcada, fixa e variavel.
def cycle_ticket_number(key: str, number: int) -> None:
    """Ciclo: desmarcada -> fixa -> variável -> desmarcada."""
    # states recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    states = st.session_state.setdefault(f"{key}_states", {})
    # order recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    order = st.session_state.setdefault(f"{key}_order", {})
    # current recebe o valor que armazena em `current` o valor obtido de `states.get(number, 0)`.
    current = states.get(number, 0)
    # Verifica se `current == 2`.
    if current == 2:
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        states.pop(number, None)
        # Chama `order.pop` para executa a operacao do objeto com os argumentos indicados.
        order.pop(number, None)
        # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
        return

    # states[number] recebe o valor que armazena em `states[number` o valor obtido de `current + 1`.
    states[number] = current + 1
    # order[number] recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    order[number] = st.session_state.get("ticket_click_counter", 0)
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    st.session_state["ticket_click_counter"] = order[number] + 1


# Mostra o volante interativo e devolve as dezenas fixas, variaveis e sua ordem.
def render_unified_ticket(key: str) -> tuple[list[int], list[int], dict[int, int]]:
    # fixed, variables, order recebe o valor que armazena em `fixed` o valor obtido de `ticket_state(key)`.
    fixed, variables, order = ticket_state(key)
    # side_left, ticket_column, side_right recebe o valor que cria as colunas da interface usadas para organizar os controles.
    side_left, ticket_column, side_right = st.columns([0.1, 3.8, 0.1])
    # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
    with ticket_column:
        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown(
            """
            <div class="ticket-card">
                <div class="ticket-header">
                    <div class="ticket-header-title">VOLANTE LOTOFÁCIL</div>
                    <div class="ticket-header-sub">1º CLIQUE: FIXA · 2º CLIQUE: VARIÁVEL · 3º CLIQUE: DESMARCA</div>
                </div>
                <div class="ticket-body">
            """,  # Fecha o fragmento HTML e o entrega ? chamada que o renderiza.
            # unsafe_allow_html recebe o valor que armazena em `unsafe_allow_html` o valor obtido de `True,`.
            unsafe_allow_html=True,
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

        # states recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
        states = st.session_state[f"{key}_states"]
        # Percorre row in range(5) e executa o bloco para cada item.
        for row in range(5):
            # columns recebe o valor que cria as colunas da interface usadas para organizar os controles.
            columns = st.columns(5, gap="small")
            # Percorre column_index in range(5) e executa o bloco para cada item.
            for column_index in range(5):
                # number recebe o valor que armazena em `number` o valor obtido de `column_index * 5 + row + 1`.
                number = column_index * 5 + row + 1
                # state recebe o valor que armazena em `state` o valor obtido de `states.get(number, 0)`.
                state = states.get(number, 0)
                # state_suffix recebe o valor que monta a colecao de valores usada pela etapa atual.
                state_suffix = ("empty", "fixed", "variable")[state]
                # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
                with columns[column_index]:
                    # Verifica se `st.button(`.
                    if st.button(
                        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                        f"{number:02d}",
                        # key recebe o valor que define o texto ou identificador `f"btn_ticket_{key}_{number}_{state_suffix}",` usado nesta etapa.
                        key=f"btn_ticket_{key}_{number}_{state_suffix}",
                        # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
                        use_container_width=True,
                    # Inicia o bloco correspondente a estrutura de controle definida nesta linha.
                    ):
                        # Compoe a expressao ou os argumentos da operacao iniciada acima.
                        cycle_ticket_number(key, number)
                        # Chama `st.rerun` para solicita uma nova renderizacao da interface.
                        st.rerun()

        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown(
            """
                </div>
                <div class="ticket-legend">
                    <span class="legend-item"><span class="legend-dot dot-fixed"></span> <b>Fixa</b> (Vinho)</span>
                    <span class="legend-item"><span class="legend-dot dot-variable"></span> <b>Variável</b> (Azul)</span>
                    <span class="legend-item"><span class="legend-dot dot-empty"></span> Não selecionada</span>
                </div>
            </div>
            """,  # Fecha o fragmento HTML e o entrega ? chamada que o renderiza.
            # unsafe_allow_html recebe o valor que armazena em `unsafe_allow_html` o valor obtido de `True,`.
            unsafe_allow_html=True,
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

    # fixed, variables, order recebe o valor que armazena em `fixed` o valor obtido de `ticket_state(key)`.
    fixed, variables, order = ticket_state(key)
    # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
    st.caption(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        f"**Fixas ({len(fixed)})**: {', '.join(f'{n:02d}' for n in fixed) or 'nenhuma'}  |  "
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        f"**Variáveis ({len(variables)})**: {', '.join(f'{n:02d}' for n in variables) or 'nenhuma'}"
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )
    # Devolve fixed, variables, order ao codigo que chamou esta funcao.
    return fixed, variables, order


# Combina dezenas fixas com a quantidade escolhida de variaveis em cada aposta.
def generate_ticket_combinations(
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    fixed: list[int], variables: list[int], pick: int, order: dict[int, int]
# Inicia o bloco correspondente a estrutura de controle definida nesta linha.
) -> list[list[int]]:
    # Verifica se `pick < 0 or pick > len(variables)`.
    if pick < 0 or pick > len(variables):
        # Interrompe o fluxo levantando o erro especificado para sinalizar uma condicao invalida.
        raise ValueError("A quantidade de dezenas variáveis por jogo é inválida.")
    # Evita produzir apostas menores por repeticao entre dezenas fixas e variaveis.
    if set(fixed) & set(variables):
        # Interrompe a geracao quando as selecoes se sobrepoem.
        raise ValueError("A mesma dezena não pode estar nas seleções fixa e variável.")
    # Calcula o numero de apostas antes de alocar a lista completa.
    combination_count = math.comb(len(variables), pick)
    # Confirma que dezenas recebidas pela funcao pertencem ao volante oficial.
    if any(number not in ALL_NUMBERS for number in fixed + variables):
        # Impede jogos com valores ausentes no volante.
        raise ValueError("As dezenas fixas e variáveis devem estar entre 01 e 25.")
    # Impede que uma configuracao gere mais apostas do que o limite de seguranca.
    if combination_count > MAX_GENERATED_GAMES:
        # Interrompe a geracao com uma explicacao e o limite permitido.
        raise ValueError(f"{combination_count:,} combinações excedem o limite de {MAX_GENERATED_GAMES:,}.".replace(",", "."))
    # Devolve [ ao codigo que chamou esta funcao.
    return [
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        sorted(fixed + list(variable_pick), key=lambda number: order[number])
        # Percorre variable_pick in combinations(variables, pick) e executa o bloco para cada item.
        for variable_pick in combinations(variables, pick)
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    ]


# Renderiza o volante usado para escolher dezenas extras do Arquivo C.
def render_extra_ticket(key: str) -> list[int]:
    """Cartela de seleção simples para as dezenas extras do Arquivo C."""
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    init_selection(key)
    # side_left, ticket_column, side_right recebe o valor que cria as colunas da interface usadas para organizar os controles.
    side_left, ticket_column, side_right = st.columns([0.1, 3.8, 0.1])
    # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
    with ticket_column:
        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown(
            """
            <div class="ticket-card">
                <div class="ticket-header" style="background: linear-gradient(135deg, #047857 0%, #10b981 100%);">
                    <div class="ticket-header-title">VARIÁVEIS EXTRAS</div>
                    <div class="ticket-header-sub">SELEÇÃO COMPLEMENTAR PARA O ARQUIVO C</div>
                </div>
                <div class="ticket-body">
            """,  # Fecha o fragmento HTML e o entrega ? chamada que o renderiza.
            # unsafe_allow_html recebe o valor que armazena em `unsafe_allow_html` o valor obtido de `True,`.
            unsafe_allow_html=True,
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

        # Percorre row in range(5) e executa o bloco para cada item.
        for row in range(5):
            # columns recebe o valor que cria as colunas da interface usadas para organizar os controles.
            columns = st.columns(5, gap="small")
            # Percorre column_index in range(5) e executa o bloco para cada item.
            for column_index in range(5):
                # number recebe o valor que armazena em `number` o valor obtido de `column_index * 5 + row + 1`.
                number = column_index * 5 + row + 1
                # selected recebe o valor que armazena em `selected` o valor obtido de `number in st.session_state[key]`.
                selected = number in st.session_state[key]
                # state_suffix recebe o valor que define o texto ou identificador `"selected" if selected else "empty"` usado nesta etapa.
                state_suffix = "selected" if selected else "empty"
                # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
                with columns[column_index]:
                    # Verifica se `st.button(`.
                    if st.button(
                        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                        f"{number:02d}",
                        # key recebe o valor que define o texto ou identificador `f"btn_extra_{key}_{number}_{state_suffix}",` usado nesta etapa.
                        key=f"btn_extra_{key}_{number}_{state_suffix}",
                        # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
                        use_container_width=True,
                    # Inicia o bloco correspondente a estrutura de controle definida nesta linha.
                    ):
                        # Compoe a expressao ou os argumentos da operacao iniciada acima.
                        toggle_number(key, number)
                        # Chama `st.rerun` para solicita uma nova renderizacao da interface.
                        st.rerun()

        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown(
            """
                </div>
                <div class="ticket-legend">
                    <span class="legend-item"><span class="legend-dot dot-extra"></span> Extra Selecionada</span>
                    <span class="legend-item"><span class="legend-dot dot-empty"></span> Livre</span>
                </div>
            </div>
            """,  # Fecha o fragmento HTML e o entrega ? chamada que o renderiza.
            # unsafe_allow_html recebe o valor que armazena em `unsafe_allow_html` o valor obtido de `True,`.
            unsafe_allow_html=True,
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

    # Devolve get_selection(key) ao codigo que chamou esta funcao.
    return get_selection(key)


# Remove as dezenas fixas de uma aposta para obter somente seu nucleo variavel.
def variable_core(game: list[int], fixed_numbers: list[int]) -> list[int]:
    # fixed_set recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
    fixed_set = set(fixed_numbers)
    # Devolve [number for number in game if number not in fixed_set] ao codigo que chamou esta funcao.
    return [number for number in game if number not in fixed_set]


# Combina os nucleos dos Arquivos A e B com dezenas extras sem repetir combinacoes.
def generate_file_c(
    # Continua a expressao composta iniciada acima com este operando.
    games_a: list[list[int]],
    # Continua a expressao composta iniciada acima com este operando.
    games_b: list[list[int]],
    # Continua a expressao composta iniciada acima com este operando.
    fixed_a: list[int],
    # Continua a expressao composta iniciada acima com este operando.
    fixed_b: list[int],
    # Continua a expressao composta iniciada acima com este operando.
    extra_variables: list[int],
    # Continua a expressao composta iniciada acima com este operando.
    target_size: int,
# Inicia o bloco correspondente a estrutura de controle definida nesta linha.
) -> list[list[int]]:
    """Combina os miolos de A e B com as variáveis extras, sem repetir dezenas."""
    # Verifica se `target_size not in BET_PRICES`.
    if target_size not in BET_PRICES:
        # Interrompe o fluxo levantando o erro especificado para sinalizar uma condicao invalida.
        raise ValueError("O Arquivo C deve ter de 15 a 20 dezenas por aposta.")

    # Limita o produto de arquivos antes de percorrer pares potencialmente enormes.
    if len(games_a) * len(games_b) > MAX_GENERATED_GAMES:
        # Informa que os arquivos de origem excedem o limite de processamento.
        raise ValueError(f"A combinação dos Arquivos A e B excede o limite de {MAX_GENERATED_GAMES:,} pares.".replace(",", "."))

    # generated recebe o valor que monta a colecao de valores usada pela etapa atual.
    generated = []
    # seen recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
    seen = set()
    # Precalcula as partes variaveis de A para nao repetir o processamento no laco interno.
    cores_a = [variable_core(game, fixed_a) for game in games_a]
    # Precalcula as partes variaveis de B antes de combinar pares de jogos.
    cores_b = [variable_core(game, fixed_b) for game in games_b]
    # Percorre game_a in games_a e executa o bloco para cada item.
    for core_a in cores_a:
        # Percorre game_b in games_b e executa o bloco para cada item.
        for core_b in cores_b:
            # base recebe o valor que armazena em `base` o valor obtido de `unique_in_selection_order(core_a + core_b)`.
            base = unique_in_selection_order(core_a + core_b)
            # needed recebe o valor que armazena em `needed` o valor obtido de `target_size - len(base)`.
            needed = target_size - len(base)
            # Verifica se `needed < 0`.
            if needed < 0:
                # Pula para a proxima repeticao do laco atual.
                continue
            # candidates recebe o valor que monta a colecao de valores usada pela etapa atual.
            candidates = [number for number in extra_variables if number not in base]
            # Ignora este par se as dezenas extras nao conseguem completar o tamanho solicitado.
            if needed > len(candidates):
                # Avanca para o proximo par sem gerar uma aposta menor que o tamanho-alvo.
                continue
            # Monta somente selecoes que completam a quantidade configurada.
            extra_picks = combinations(candidates, needed)
            # Percorre extra_pick in extra_picks e executa o bloco para cada item.
            for extra_pick in extra_picks:
                # Ordena a aposta para que jogos iguais tenham uma unica representacao.
                game = sorted(base + list(extra_pick))
                # Usa a aposta ordenada como chave de deduplicacao entre pares.
                signature = tuple(game)
                # Verifica se `signature not in seen`.
                if signature not in seen:
                    # Compoe a expressao ou os argumentos da operacao iniciada acima.
                    seen.add(signature)
                    # Chama `generated.append` para executa a operacao do objeto com os argumentos indicados.
                    generated.append(game)
                    # Interrompe cedo se a combinacao ultrapassar o limite de jogos configurado.
                    if len(generated) > MAX_GENERATED_GAMES:
                        # Informa o tamanho maximo permitido para o Arquivo C.
                        raise ValueError(f"O Arquivo C excede o limite de {MAX_GENERATED_GAMES:,} jogos.".replace(",", "."))
    # Devolve generated ao codigo que chamou esta funcao.
    return generated


# Transfere texto ou uma colecao de jogos para o conferidor e seleciona sua tela.
def send_games_to_checker(games: str | list[list[int]] | None, error_key: str = "checker_navigation_error") -> None:
    # Converte jogos em linhas de texto ou mantem o texto recebido diretamente.
    games_text = games if isinstance(games, str) else "\n".join(format_game(game) for game in games or [])
    # Rejeita a navegacao se nao houver jogos para transferir.
    if not games_text:
        # Sinaliza ao modulo de origem que nenhum jogo estava disponivel.
        st.session_state[error_key] = True
        # Encerra a funcao antes de alterar o estado do conferidor.
        return
    # Preenche o campo de texto do conferidor.
    st.session_state["checker_games_text"] = games_text
    # Seleciona o modo de entrada por texto.
    st.session_state["checker_input_method"] = "Colar texto"
    # Abre a secao do conferidor.
    st.session_state["active_section"] = "Conferidor"
    # Agenda a busca automatica de concursos recentes.
    st.session_state["auto_check_pending"] = True


# Envia os jogos do gerador principal ao conferidor.
def open_generated_games_in_checker() -> None:
    # Recupera o texto produzido pelo gerador principal.
    send_games_to_checker(st.session_state.get("generated_games_txt"))


# Gera combinacoes a partir dos grupos selecionados na nova area.
def generate_group_games() -> None:
    # Usa os intervalos padronizados definidos nas constantes do modulo.
    ranges = GROUP_RANGES
    # Prepara os grupos com os estados atualizados das caixas e seletores.
    groups = []
    # Percorre cada faixa para montar os dados combinatorios atuais.
    for group_index, group_range in enumerate(ranges):
        # Recupera somente as dezenas marcadas na faixa atual.
        selected = [number for number in group_range if st.session_state.get(f"group_number_{number}", number in GROUP_DEFAULT_SELECTED_NUMBERS)]
        # Recupera quantas dezenas devem ser escolhidas nesta faixa.
        pick = int(st.session_state.get(f"group_pick_{group_index}", GROUP_DEFAULT_PICKS[group_index]))
        # Inclui a faixa quando existe quantidade positiva para selecionar.
        if selected and pick:
            # Guarda as dezenas e sua quantidade escolhida.
            groups.append((selected, pick))
    # Sincroniza a configuracao visivel com os valores usados nesta geracao.
    st.session_state["group_generation_config"] = groups
    # Soma quantas dezenas compoem cada aposta configurada.
    numbers_per_game = sum(pick for _, pick in groups)
    # Impede a geracao de jogos sem dezenas.
    if not groups or not 15 <= numbers_per_game <= 20:
        st.session_state["group_generation_error"] = "Configure entre 15 e 20 dezenas por jogo antes de gerar."
        return
    # Calcula o total esperado antes de construir os jogos.
    total_games = expected_combination_count(groups)
    # Impede a geracao acima do limite antes de alocar memoria.
    if total_games > MAX_GENERATED_GAMES:
        # Deixa uma mensagem para a interface mostrar ao usuario.
        st.session_state["group_generation_error"] = f"{total_games:,} combinações excedem o limite de {MAX_GENERATED_GAMES:,}.".replace(",", ".")
        # Encerra sem materializar uma lista grande.
        return
    # Gera o produto de combinacoes de todos os grupos.
    try:
        # Produz as apostas com deteccao de sobreposicoes e limite global.
        games = generate_combinations([], groups)
    # Converte erros de configuracao em mensagens visiveis no modulo.
    except ValueError as exc:
        # Preserva a explicacao gerada pela rotina de combinacoes.
        st.session_state["group_generation_error"] = str(exc)
        # Encerra sem substituir os jogos anteriores.
        return
    # Armazena os jogos para exibicao e para os botoes de encaminhamento.
    st.session_state["group_generated_games"] = games
    # Armazena os jogos em linhas de texto para os outros modulos.
    st.session_state["group_generated_games_txt"] = "\n".join(format_game(game) for game in games)


# Leva os jogos deste modulo ao conferidor.
def open_group_games_in_checker() -> None:
    # Envia o texto do modulo de grupos usando a rotina compartilhada.
    send_games_to_checker(st.session_state.get("group_generated_games_txt"), "group_generation_error")


# Leva os jogos deste modulo ao impressor de volantes.
def open_group_games_in_printer() -> None:
    # Recupera as apostas que foram geradas neste modulo.
    games_text = st.session_state.get("group_generated_games_txt", "")
    # Informa a interface se ainda nao existem apostas para encaminhar.
    if not games_text:
        st.session_state["group_generation_error"] = "Gere as combinacoes antes de enviar para impressao."
        return
    # Coloca as apostas no campo de texto do impressor.
    st.session_state["print_games_text"] = games_text
    # Abre a secao de impressao.
    st.session_state["active_section"] = "Imprimir Folha Loto"


# Prepara os jogos do Arquivo C e navega ao conferidor.
def open_intersection_c_in_checker() -> None:
    # games recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    games = st.session_state.get("intersection_c_games", [])
    # Transfere os jogos de C para o conferidor.
    send_games_to_checker(games)


# Cria o callback que transfere um Arquivo A ou B para o conferidor.
def make_open_intersection_ab_in_checker(letter: str):
    """Fábrica de callbacks para abrir Arquivo A ou B no conferidor."""
    # Prepara os jogos do arquivo selecionado e navega ao conferidor.
    def _callback() -> None:
        # key recebe o valor que define o texto ou identificador `f"intersection_{letter.lower()}_games"` usado nesta etapa.
        key = f"intersection_{letter.lower()}_games"
        # games recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
        games = st.session_state.get(key, [])
        # Transfere os jogos de A ou B usando a funcao comum de navegacao.
        send_games_to_checker(games)
    # Devolve _callback ao codigo que chamou esta funcao.
    return _callback


# Gera o produto cartesiano das escolhas de dezenas nos grupos configurados.
def generate_combinations(
    # fixed recebe o valor que armazena em `fixed` o valor obtido de `True`.
    fixed: list[int], groups: list[tuple[list[int], int]], fixed_first: bool = True
# Inicia o bloco correspondente a estrutura de controle definida nesta linha.
) -> list[list[int]]:
    # fixed_unique recebe o valor que armazena em `fixed_unique` o valor obtido de `unique_in_selection_order(fixed)`.
    fixed_unique = unique_in_selection_order(fixed)

    # Rejeita dezenas fixas que nao existem no volante antes de calcular combinacoes.
    if any(number not in ALL_NUMBERS for number in fixed_unique):
        # Informa os limites validos aceitos pelo gerador.
        raise ValueError("As dezenas fixas devem estar entre 01 e 25.")

    # Confirma que todas as dezenas de cada grupo pertencem ao volante oficial.
    if any(number not in ALL_NUMBERS for numbers, _ in groups for number in numbers):
        # Impede que uma combinacao contenha dezenas fora da cartela.
        raise ValueError("As dezenas dos grupos devem estar entre 01 e 25.")

    # Rejeita dezenas repetidas entre faixas para evitar jogos menores ou duplicados.
    overlap_warnings = find_overlap_warnings(fixed_unique, groups)
    # Interrompe a geracao quando as faixas produzem sobreposicoes.
    if overlap_warnings:
        # Mostra o primeiro conflito encontrado entre selecoes.
        raise ValueError(overlap_warnings[0])

    # Verifica se `not groups`.
    if not groups:
        # Devolve [fixed_unique] if fixed_unique else [] ao codigo que chamou esta funcao.
        return [fixed_unique] if fixed_unique else []

    # Calcula quantas combinacoes serao criadas antes de materializa-las.
    combination_count = expected_combination_count(groups)
    # Protege a memoria contra configuracoes que gerem listas excessivamente grandes.
    if combination_count > MAX_GENERATED_GAMES:
        # Interrompe a operacao com o total previsto e o limite aplicado.
        raise ValueError(f"{combination_count:,} combinações excedem o limite de {MAX_GENERATED_GAMES:,}.".replace(",", "."))

    # group_combos recebe o valor que monta a colecao de valores usada pela etapa atual.
    group_combos = []
    # Percorre numbers, pick in groups e executa o bloco para cada item.
    for numbers, pick in groups:
        # unique recebe o valor que armazena em `unique` o valor obtido de `unique_in_selection_order(numbers)`.
        unique = unique_in_selection_order(numbers)
        # Verifica se `pick < 0`.
        if pick < 0:
            # Interrompe o fluxo levantando o erro especificado para sinalizar uma condicao invalida.
            raise ValueError("A quantidade a escolher não pode ser negativa.")
        # Verifica se `pick > len(unique)`.
        if pick > len(unique):
            # Interrompe o fluxo levantando o erro especificado para sinalizar uma condicao invalida.
            raise ValueError(
                # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                f"Grupo [{', '.join(f'{n:02d}' for n in unique)}]: "
                # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                f"escolher {pick} dezenas, mas só há {len(unique)} disponíveis."
            # Fecha o agrupamento da chamada ou colecao iniciada acima.
            )
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        group_combos.append(list(combinations(unique, pick)))

    # games recebe o valor que monta a colecao de valores usada pela etapa atual.
    games = []
    # Percorre picks in itertools.product(*group_combos) e executa o bloco para cada item.
    for picks in itertools.product(*group_combos):
        # variable_numbers recebe o valor que monta a colecao de valores usada pela etapa atual.
        variable_numbers = [n for group in picks for n in group]
        # numbers recebe o valor que armazena em `numbers` o valor obtido de `fixed_unique + variable_numbers if fixed_first else variable_numb`.
        numbers = fixed_unique + variable_numbers if fixed_first else variable_numbers + fixed_unique
        # game recebe o valor que armazena em `game` o valor obtido de `unique_in_selection_order(numbers)`.
        game = unique_in_selection_order(numbers)
        # Chama `games.append` para executa a operacao do objeto com os argumentos indicados.
        games.append(game)
    # Devolve games ao codigo que chamou esta funcao.
    return games


# Calcula quantas combinacoes resultam dos tamanhos de grupos escolhidos.
def expected_combination_count(groups: list[tuple[list[int], int]]) -> int:
    # total recebe o valor que armazena em `total` o valor obtido de `1`.
    total = 1
    # Percorre numbers, pick in groups e executa o bloco para cada item.
    for numbers, pick in groups:
        # n recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
        n = len(set(numbers))
        # Verifica se `pick > n or pick < 0`.
        if pick > n or pick < 0:
            # Devolve 0 ao codigo que chamou esta funcao.
            return 0
        # Atualiza `total` com o resultado da operacao `*=` aplicada a `math.comb(n, pick)`.
        total *= math.comb(n, pick)
    # Devolve total ao codigo que chamou esta funcao.
    return total


# Soma as dezenas fixas e as quantidades escolhidas nos grupos.
def configured_dezenas_count(fixed: list[int], groups: list[tuple[list[int], int]]) -> int:
    # Devolve len(set(fixed)) + sum(pick for _, pick in groups) ao codigo que chamou esta funcao.
    return len(set(fixed)) + sum(pick for _, pick in groups)


# Identifica dezenas repetidas entre selecoes fixas e grupos variaveis.
def find_overlap_warnings(fixed: list[int], groups: list[tuple[list[int], int]]) -> list[str]:
    # warnings recebe o valor que monta a colecao de valores usada pela etapa atual.
    warnings = []
    # fixed_set recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
    fixed_set = set(fixed)

    # seen_in_groups recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
    seen_in_groups: set[int] = set()
    # Percorre idx, (numbers, _) in enumerate(groups, start=1) e executa o bloco para cada item.
    for idx, (numbers, _) in enumerate(groups, start=1):
        # group_set recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
        group_set = set(numbers)
        # overlap_fixed recebe o valor que armazena em `overlap_fixed` o valor obtido de `group_set & fixed_set`.
        overlap_fixed = group_set & fixed_set
        # Verifica se `overlap_fixed`.
        if overlap_fixed:
            # nums recebe o valor que define o texto ou identificador `", ".join(f"{n:02d}" for n in sorted(overlap_` usado nesta etapa.
            nums = ", ".join(f"{n:02d}" for n in sorted(overlap_fixed))
            # Chama `warnings.append` para executa a operacao do objeto com os argumentos indicados.
            warnings.append(f"Grupo {idx} repete dezenas fixas: {nums}.")

        # overlap_groups recebe o valor que armazena em `overlap_groups` o valor obtido de `group_set & seen_in_groups`.
        overlap_groups = group_set & seen_in_groups
        # Verifica se `overlap_groups`.
        if overlap_groups:
            # nums recebe o valor que define o texto ou identificador `", ".join(f"{n:02d}" for n in sorted(overlap_` usado nesta etapa.
            nums = ", ".join(f"{n:02d}" for n in sorted(overlap_groups))
            # Chama `warnings.append` para executa a operacao do objeto com os argumentos indicados.
            warnings.append(f"Grupo {idx} repete dezenas de outro grupo: {nums}.")

        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        seen_in_groups |= group_set

    # Devolve warnings ao codigo que chamou esta funcao.
    return warnings


# Converte o formato oficial da CAIXA para os campos usados pelo conferidor.
def normalize_caixa_result(payload: dict) -> dict:
    # Confirma que o endpoint respondeu com um objeto JSON.
    if not isinstance(payload, dict):
        # Sinaliza um formato externo que o aplicativo nao consegue interpretar.
        raise ValueError("A API da CAIXA retornou uma resposta em formato inesperado.")
    # Verifica todos os campos oficiais necessarios para conferir um concurso.
    required_fields = {"numero", "dataApuracao", "listaDezenas", "listaRateioPremio"}
    # Calcula quais campos obrigatorios faltaram na resposta.
    missing_fields = required_fields - payload.keys()
    # Reporta mudancas no esquema da API sem derrubar a tela do conferidor.
    if missing_fields:
        # Informa quais campos estao ausentes para facilitar diagnostico.
        raise ValueError("A resposta da CAIXA nao contem os campos esperados: " + ", ".join(sorted(missing_fields)))
    # Valida que dezenas e faixas de premio vieram como listas.
    if not isinstance(payload["listaDezenas"], list) or not isinstance(payload["listaRateioPremio"], list):
        # Evita continuar com dados que nao podem ser iterados com seguranca.
        raise ValueError("A API da CAIXA retornou dezenas ou faixas em formato inesperado.")
    # Converte as faixas oficiais em uma lista simples de premiacoes.
    prizes = []
    # Percorre cada faixa oficial de premios do concurso.
    for item in payload["listaRateioPremio"]:
        # Garante que cada faixa tenha texto descritivo e valor de premio.
        if not isinstance(item, dict) or "descricaoFaixa" not in item or "valorPremio" not in item:
            # Informa que a API alterou o conteudo de uma faixa de premio.
            raise ValueError("A API da CAIXA retornou uma faixa de premio em formato inesperado.")
        # Preserva descricao, premio e numero da faixa para compatibilidade futura.
        prizes.append({"descricao": item["descricaoFaixa"], "valorPremio": item["valorPremio"], "faixa": item.get("faixa")})
    # Devolve o concurso no modelo interno que o restante do conferidor espera.
    return {"concurso": payload["numero"], "data": payload["dataApuracao"], "dezenas": payload["listaDezenas"], "premiacoes": prizes}


# Devolve uma sessao HTTP com retry, isolada para a thread atual.
def get_api_session() -> requests.Session:
    # Recupera a conexao local da thread ou cria uma nova quando necessario.
    session = getattr(API_THREAD_LOCAL, "session", None)
    # Cria uma sessao independente para a thread que esta fazendo a consulta.
    if session is None:
        # Inicializa o cliente HTTP persistente desta thread.
        session = requests.Session()
        # Define cabecalhos compartilhados pelas consultas a API oficial.
        session.headers.update({"Accept": "application/json, text/plain, */*", "User-Agent": "Mozilla/5.0 LotofacilApp/1.0"})
        # Configura repeticoes limitadas para erros de conexao e respostas temporarias.
        retry = Retry(total=3, connect=3, read=2, status=2, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=frozenset({"GET"}))
        # Cria um adaptador HTTPS que aplica a politica de retry.
        adapter = HTTPAdapter(max_retries=retry)
        # Instala o adaptador para requisicoes seguras.
        session.mount("https://", adapter)
        # Associa a sessao a thread para reutilizar conexao sem compartilha-la entre threads.
        API_THREAD_LOCAL.session = session
    # Devolve a sessao persistente da thread atual.
    return session


# Cacheia por cinco minutos o resultado que pode mudar apos um novo sorteio.
@st.cache_data(ttl=300, show_spinner=False)
# Busca na API o resultado mais recente da Lotofacil.
def fetch_latest_result() -> dict:
    # Consulta o endpoint oficial com limite de tempo para evitar espera indefinida.
    response = get_api_session().get(API_URL, timeout=(5, 15))
    # Chama `response.raise_for_status` para interrompe a consulta quando a API retorna erro HTTP.
    response.raise_for_status()
    # Converte a resposta oficial para os campos esperados pelo aplicativo.
    return normalize_caixa_result(response.json())


# Cacheia indefinidamente resultados de concursos anteriores, que nao se alteram.
@st.cache_data(ttl=None, show_spinner=False)
# Busca na API o resultado do concurso solicitado.
def fetch_contest_result(contest: int) -> dict:
    # Consulta o concurso solicitado diretamente na API oficial.
    response = get_api_session().get(API_CONTEST_URL.format(contest=contest), timeout=(5, 15))
    # Chama `response.raise_for_status` para interrompe a consulta quando a API retorna erro HTTP.
    response.raise_for_status()
    # Converte a resposta oficial para os campos esperados pelo aplicativo.
    return normalize_caixa_result(response.json())


# Converte a data textual do resultado para um objeto date.
def result_date(result: dict) -> date:
    # Devolve datetime.strptime(result["data"], "%d/%m/%Y").date() ao codigo que chamou esta funcao.
    return datetime.strptime(result["data"], "%d/%m/%Y").date()


# Busca um conjunto de concursos em paralelo respeitando o cache individual.
def fetch_contests_parallel(contests: list[int]) -> list[dict]:
    # Cria um grupo limitado de workers para reduzir o tempo das consultas historicas.
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Mantem a ordem dos concursos informados ao coletar as respostas.
        return list(executor.map(fetch_contest_result, contests))


# Percorre concursos anteriores e devolve os resultados dentro do intervalo de datas.
def fetch_results_for_dates(start: date, end: date) -> list[dict]:
    # latest recebe o valor que armazena em `latest` o valor obtido de `fetch_latest_result()`.
    latest = fetch_latest_result()
    # Calcula quantos dias de historico precisam ser consultados ate a data inicial.
    calendar_days_back = max(0, (result_date(latest) - start).days) + 14
    # Converte a quantidade de dias em um limite conservador de concursos anteriores.
    latest_contest = int(latest["concurso"])
    # Cria os numeros de concurso necessarios sem consultar valores menores que um.
    contest_numbers = list(range(latest_contest - 1, max(0, latest_contest - calendar_days_back), -1))
    # Consulta o historico solicitado com concorrencia limitada e cache por concurso.
    previous_results = fetch_contests_parallel(contest_numbers)
    # Combina o ultimo concurso e o historico obtido em paralelo.
    results = [latest, *previous_results]
    # Retem apenas concursos dentro do intervalo escolhido pelo usuario.
    results = [item for item in results if start <= result_date(item) <= end]
    # Devolve os concursos em ordem cronologica crescente.
    return sorted(results, key=lambda item: int(item["concurso"]))


# Busca os concursos recentes solicitados e os ordena do mais novo para o mais antigo.
def fetch_recent_results(count: int = 10) -> list[dict]:
    # latest recebe o valor que armazena em `latest` o valor obtido de `fetch_latest_result()`.
    latest = fetch_latest_result()
    # Le o numero mais recente para definir a faixa de concursos a consultar.
    latest_contest = int(latest["concurso"])
    # Define os concursos anteriores sem ultrapassar o inicio do historico.
    contest_numbers = list(range(latest_contest - 1, max(0, latest_contest - max(count, 1)), -1))
    # Consulta concursos anteriores em paralelo, usando o cache persistente.
    previous_results = fetch_contests_parallel(contest_numbers)
    # Combina o resultado mais recente com os anteriores.
    results = [latest, *previous_results]
    # Devolve os concursos mais recentes primeiro.
    return sorted(results, key=lambda item: int(item["concurso"]), reverse=True)


# Conta quantas dezenas da aposta coincidem com o resultado sorteado.
def count_hits(game: list[int], drawn: set[int]) -> int:
    # Devolve len(set(game) & drawn) ao codigo que chamou esta funcao.
    return len(set(game) & drawn)


# Calcula quantas apostas simples premiadas existem dentro de uma aposta multipla.
def prize_units(game_size: int, hits: int) -> dict[int, int]:
    # Verifica se `game_size not in BET_PRICES`.
    if game_size not in BET_PRICES:
        # Devolve {points: 0 for points in range(11, 16)} ao codigo que chamou esta funcao.
        return {points: 0 for points in range(11, 16)}
    # misses recebe o valor que armazena em `misses` o valor obtido de `game_size - hits`.
    misses = game_size - hits
    # Devolve { ao codigo que chamou esta funcao.
    return {
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        points: math.comb(hits, points) * math.comb(misses, 15 - points)
        # Verifica se `hits >= points and misses >= 15 - points`.
        if hits >= points and misses >= 15 - points
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        else 0
        # Percorre points in range(11, 16) e executa o bloco para cada item.
        for points in range(11, 16)
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    }


# Organiza os valores de premio da resposta da API por quantidade de acertos.
def prizes_by_points(result: dict) -> dict[int, float]:
    # Cria o mapeamento que sera preenchido com as faixas interpretadas.
    prizes = {}
    # Percorre as faixas sem assumir que a descricao sempre comeca com um numero.
    for item in result.get("premiacoes", []):
        # Le uma descricao vazia quando a API nao envia texto para a faixa.
        description = str(item.get("descricao", ""))
        # Procura explicitamente o numero de acertos no texto da faixa.
        match = re.search(r"\b(1[1-5])\b", description)
        # Recupera o identificador numerico oficial quando a descricao mudou.
        points = int(match.group(1)) if match else 16 - int(item["faixa"]) if item.get("faixa") in {1, 2, 3, 4, 5} else None
        # Ignora faixas que nao possam ser associadas a 11 a 15 acertos.
        if points not in range(11, 16):
            # Continua a leitura das demais faixas validas.
            continue
        # Armazena o premio unitario da faixa identificada.
        prizes[points] = float(item.get("valorPremio", 0) or 0)
    # Devolve os premios organizados por quantidade de acertos.
    return prizes


# Formata um valor numerico como moeda brasileira.
def brl(value: float) -> str:
    # Devolve f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") ao codigo que chamou esta funcao.
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Recorte do scanner do volante Lotofácil em assets/volante-lotofacil-scanner.jpg.
# VOLANTE_SOURCE_PATH aponta para a imagem escaneada usada como base do volante impresso.
VOLANTE_SOURCE_PATH = Path(__file__).parent / "assets" / "volante-lotofacil-scanner.jpg"
# VOLANTE_IMAGE_SIZE define a resolucao de referencia do recorte escaneado.
VOLANTE_IMAGE_SIZE = (651, 1496)
# VOLANTE_PRINT_WIDTH converte a largura fisica de 8,2 cm para pontos PDF.
VOLANTE_PRINT_WIDTH = 8.2 * 72 / 2.54  # 8,2 cm
# VOLANTE_PRINT_HEIGHT converte a altura fisica de 14 cm para pontos PDF.
VOLANTE_PRINT_HEIGHT = 14 * 72 / 2.54  # 14 cm
# VOLANTES_PER_PAGE define a capacidade fixa de quatro volantes por pagina A4.
VOLANTES_PER_PAGE = 4

# Cada volante escaneado tem três jogos e cinco colunas: 21-25, 16-20,
# 11-15, 06-10 e 01-05. As coordenadas são centros das casas no recorte.
# VOLANTE_COLUMN_X guarda os centros horizontais das cinco colunas de dezenas no recorte.
VOLANTE_COLUMN_X = (106, 205, 304, 404, 503)
# VOLANTE_ROW_Y guarda os centros verticais das casas nos tres jogos do volante.
VOLANTE_ROW_Y = (
    # Continua a expressao composta iniciada acima com este operando.
    (363, 399, 434, 469, 505),
    # Continua a expressao composta iniciada acima com este operando.
    (563, 599, 634, 669, 705),
    # Continua a expressao composta iniciada acima com este operando.
    (762, 797, 832, 867, 903),
# Fecha o agrupamento da chamada ou colecao iniciada acima.
)
# VOLANTE_MARK_WIDTH define a largura do preenchimento impresso sobre uma dezena.
VOLANTE_MARK_WIDTH = 20
# VOLANTE_MARK_HEIGHT define a altura do preenchimento impresso sobre uma dezena.
VOLANTE_MARK_HEIGHT = 23
# VOLANTE_SIZE_OPTION_X guarda as posicoes horizontais das opcoes de quantidade de dezenas.
VOLANTE_SIZE_OPTION_X = (100, 150, 201, 252, 303, 355)
# VOLANTE_SIZE_OPTION_Y define a posicao vertical das opcoes de quantidade de dezenas.
VOLANTE_SIZE_OPTION_Y = 963
# VOLANTE_SIZE_MARK_WIDTH define a largura do preenchimento da quantidade de dezenas.
VOLANTE_SIZE_MARK_WIDTH = 18
# VOLANTE_SIZE_MARK_HEIGHT define a altura do preenchimento da quantidade de dezenas.
VOLANTE_SIZE_MARK_HEIGHT = 12


# Aplica o decorador st.cache_data a funcao definida logo abaixo.
@st.cache_data(show_spinner=False)
# Carrega o recorte escaneado e o serializa como imagem JPEG para o PDF.
def load_volante_template() -> bytes:
    """Carrega o recorte em pé do volante obtido do scanner A4."""
    # Interrompe com uma mensagem direta se o arquivo de imagem nao estiver instalado.
    if not VOLANTE_SOURCE_PATH.is_file():
        # Informa o caminho esperado para restaurar o recurso ausente.
        raise FileNotFoundError(f"Imagem do volante nao encontrada: {VOLANTE_SOURCE_PATH}")
    # template recebe o valor que armazena em `template` o valor obtido de `Image.open(VOLANTE_SOURCE_PATH).convert("RGB")`.
    template = Image.open(VOLANTE_SOURCE_PATH).convert("RGB")
    # Verifica se `template.size != VOLANTE_IMAGE_SIZE`.
    if template.size != VOLANTE_IMAGE_SIZE:
        # template recebe o valor que armazena em `template` o valor obtido de `template.resize(VOLANTE_IMAGE_SIZE, Image.Resampling.LANCZOS)`.
        template = template.resize(VOLANTE_IMAGE_SIZE, Image.Resampling.LANCZOS)
    # buffer recebe o valor que armazena em `buffer` o valor obtido de `BytesIO()`.
    buffer = BytesIO()
    # template.save(buffer, format recebe o valor que define o texto ou identificador `"JPEG", quality=95)` usado nesta etapa.
    template.save(buffer, format="JPEG", quality=95)
    # Devolve buffer.getvalue() ao codigo que chamou esta funcao.
    return buffer.getvalue()


# Calcula as coordenadas do retangulo que preenche uma dezena no volante.
def volante_mark_position(board_index: int, number: int) -> tuple[float, float, float, float]:
    """Retorna a área interna a ser preenchida para uma dezena do volante."""
    # row recebe o valor que monta a colecao de valores usada pela etapa atual.
    row = (number - 1) % 5
    # column recebe o valor que armazena em `column` o valor obtido de `4 - ((number - 1) // 5)`.
    column = 4 - ((number - 1) // 5)
    # x recebe o valor que armazena em `x` o valor obtido de `VOLANTE_COLUMN_X[column] - VOLANTE_MARK_WIDTH / 2`.
    x = VOLANTE_COLUMN_X[column] - VOLANTE_MARK_WIDTH / 2
    # y recebe o valor que armazena em `y` o valor obtido de `VOLANTE_ROW_Y[board_index][row] - VOLANTE_MARK_HEIGHT / 2`.
    y = VOLANTE_ROW_Y[board_index][row] - VOLANTE_MARK_HEIGHT / 2
    # Devolve x, y, VOLANTE_MARK_WIDTH, VOLANTE_MARK_HEIGHT ao codigo que chamou esta funcao.
    return x, y, VOLANTE_MARK_WIDTH, VOLANTE_MARK_HEIGHT


# Agrupa apostas de mesmo tamanho em volantes com ate tres jogos cada.
def group_print_cards(games: list[list[int]]) -> list[tuple[int, list[list[int]]]]:
    """Agrupa jogos por tamanho para manter correta a seleção compartilhada."""
    # games_by_size recebe o valor que monta a colecao de valores usada pela etapa atual.
    games_by_size: dict[int, list[list[int]]] = {}
    # Percorre game in games e executa o bloco para cada item.
    for game in games:
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        games_by_size.setdefault(len(game), []).append(game)
    # Devolve [ ao codigo que chamou esta funcao.
    return [
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        (size, games_by_size[size][start:start + 3])
        # Percorre size in sorted(games_by_size) e executa o bloco para cada item.
        for size in sorted(games_by_size)
        # Percorre start in range(0, len(games_by_size[size]), 3) e executa o bloco para cada item.
        for start in range(0, len(games_by_size[size]), 3)
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    ]


# Calcula quantas paginas A4 sao necessarias para os volantes agrupados.
def print_page_count(games: list[list[int]]) -> int:
    """Calcula folhas A4 agrupando três apostas iguais por volante."""
    # cards recebe o valor que armazena em `cards` o valor obtido de `group_print_cards(games)`.
    cards = group_print_cards(games)
    # Devolve math.ceil(len(cards) / VOLANTES_PER_PAGE) if cards else 0 ao codigo que chamou esta funcao.
    return math.ceil(len(cards) / VOLANTES_PER_PAGE) if cards else 0


# Calcula onde preencher no volante a quantidade de dezenas da aposta.
def volante_size_mark_position(game_size: int) -> tuple[float, float, float, float]:
    """Retorna a área a preencher para a quantidade de dezenas selecionada."""
    # x recebe o valor que armazena em `x` o valor obtido de `VOLANTE_SIZE_OPTION_X[game_size - 15]`.
    x = VOLANTE_SIZE_OPTION_X[game_size - 15]
    # y recebe o valor que armazena em `y` o valor obtido de `VOLANTE_SIZE_OPTION_Y`.
    y = VOLANTE_SIZE_OPTION_Y
    # Devolve ( ao codigo que chamou esta funcao.
    return (
        # Continua a expressao composta iniciada acima com este operando.
        x - VOLANTE_SIZE_MARK_WIDTH / 2,
        # Continua a expressao composta iniciada acima com este operando.
        y - VOLANTE_SIZE_MARK_HEIGHT / 2,
        # Continua a expressao composta iniciada acima com este operando.
        VOLANTE_SIZE_MARK_WIDTH,
        # Continua a expressao composta iniciada acima com este operando.
        VOLANTE_SIZE_MARK_HEIGHT,
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )


# Desenha uma casa do volante usando origem superior, escala e deslocamentos comuns.
def draw_volante_mark(pdf, rect: tuple[float, float, float, float], scale_x: float, scale_y: float, origin_x: float = 0.0, origin_top: float = VOLANTE_PRINT_HEIGHT, offset_x: float = 0.0, offset_y: float = 0.0) -> None:
    # Separa posicao e dimensoes da casa medidas no recorte original.
    mark_x, mark_y, mark_width, mark_height = rect
    # Converte x da origem superior esquerda para coordenada PDF.
    x = origin_x + mark_x * scale_x + offset_x
    # Converte y medido do topo para coordenada inferior usada pelo PDF.
    y = origin_top - (mark_y + mark_height) * scale_y + offset_y
    # Desenha somente o retangulo preto preenchido sem contorno.
    pdf.rect(x, y, mark_width * scale_x, mark_height * scale_y, fill=1, stroke=0)


# Gera paginas A4 com os jogos marcados e linhas alinhadas para corte.
def build_games_pdf(games: list[list[int]]) -> bytes:
    """Cria A4 retrato com grade fixa de quatro volantes em escala real."""
    # output recebe o valor que armazena em `output` o valor obtido de `BytesIO()`.
    output = BytesIO()
    # page_width, page_height recebe o valor que armazena em `page_width` o valor obtido de `A4`.
    page_width, page_height = A4
    # pdf recebe o valor que armazena em `pdf` o valor obtido de `canvas.Canvas(output, pagesize=(page_width, page_height))`.
    pdf = canvas.Canvas(output, pagesize=(page_width, page_height))
    # grid_width recebe o valor que armazena em `grid_width` o valor obtido de `2 * VOLANTE_PRINT_WIDTH`.
    grid_width = 2 * VOLANTE_PRINT_WIDTH
    # grid_height recebe o valor que armazena em `grid_height` o valor obtido de `2 * VOLANTE_PRINT_HEIGHT`.
    grid_height = 2 * VOLANTE_PRINT_HEIGHT
    # left recebe o valor que monta a colecao de valores usada pela etapa atual.
    left = (page_width - grid_width) / 2
    # bottom recebe o valor que monta a colecao de valores usada pela etapa atual.
    bottom = (page_height - grid_height) / 2
    # scale_x recebe o valor que armazena em `scale_x` o valor obtido de `VOLANTE_PRINT_WIDTH / VOLANTE_IMAGE_SIZE[0]`.
    scale_x = VOLANTE_PRINT_WIDTH / VOLANTE_IMAGE_SIZE[0]
    # scale_y recebe o valor que armazena em `scale_y` o valor obtido de `VOLANTE_PRINT_HEIGHT / VOLANTE_IMAGE_SIZE[1]`.
    scale_y = VOLANTE_PRINT_HEIGHT / VOLANTE_IMAGE_SIZE[1]
    # template recebe o valor que armazena em `template` o valor obtido de `ImageReader(BytesIO(load_volante_template()))`.
    template = ImageReader(BytesIO(load_volante_template()))

    # cards recebe o valor que armazena em `cards` o valor obtido de `group_print_cards(games)`.
    cards = group_print_cards(games)
    # Percorre first_card in range(0, len(cards), VOLANTES_PER_PAGE) e executa o bloco para cada item.
    for first_card in range(0, len(cards), VOLANTES_PER_PAGE):
        # page_cards recebe o valor que armazena em `page_cards` o valor obtido de `cards[first_card:first_card + VOLANTES_PER_PAGE]`.
        page_cards = cards[first_card:first_card + VOLANTES_PER_PAGE]
        # Percorre card_index, (game_size, card_games) in enumerate(page_cards) e executa o bloco para cada item.
        for card_index, (game_size, card_games) in enumerate(page_cards):
            # column recebe o valor que armazena em `column` o valor obtido de `card_index % 2`.
            column = card_index % 2
            # row_from_top recebe o valor que armazena em `row_from_top` o valor obtido de `card_index // 2`.
            row_from_top = card_index // 2
            # card_left recebe o valor que armazena em `card_left` o valor obtido de `left + column * VOLANTE_PRINT_WIDTH`.
            card_left = left + column * VOLANTE_PRINT_WIDTH
            # card_bottom recebe o valor que armazena em `card_bottom` o valor obtido de `bottom + (1 - row_from_top) * VOLANTE_PRINT_HEIGHT`.
            card_bottom = bottom + (1 - row_from_top) * VOLANTE_PRINT_HEIGHT
            # Chama `pdf.drawImage` para desenha o scan do volante na posicao calculada do PDF.
            pdf.drawImage(
                # Continua a expressao composta iniciada acima com este operando.
                template,
                # Continua a expressao composta iniciada acima com este operando.
                card_left,
                # Continua a expressao composta iniciada acima com este operando.
                card_bottom,
                # width recebe o valor que armazena em `width` o valor obtido de `VOLANTE_PRINT_WIDTH,`.
                width=VOLANTE_PRINT_WIDTH,
                # height recebe o valor que armazena em `height` o valor obtido de `VOLANTE_PRINT_HEIGHT,`.
                height=VOLANTE_PRINT_HEIGHT,
            # Fecha o agrupamento da chamada ou colecao iniciada acima.
            )
            # Percorre board_index, game in enumerate(card_games) e executa o bloco para cada item.
            for board_index, game in enumerate(card_games):
                # Chama `pdf.setFillColorRGB` para executa a operacao do objeto com os argumentos indicados.
                pdf.setFillColorRGB(0, 0, 0)
                # Percorre number in set(game) e executa o bloco para cada item.
                for number in set(game):
                    # Desenha a dezena na pagina considerando a origem da cartela atual.
                    draw_volante_mark(pdf, volante_mark_position(board_index, number), scale_x, scale_y, card_left, card_bottom + VOLANTE_PRINT_HEIGHT)
            # Verifica se `game_size in BET_PRICES`.
            if game_size in BET_PRICES:
                # Desenha a quantidade de dezenas na mesma cartela do A4.
                draw_volante_mark(pdf, volante_size_mark_position(game_size), scale_x, scale_y, card_left, card_bottom + VOLANTE_PRINT_HEIGHT)

        # Contorno compartilhado das quatro cartelas e linhas fixas para corte em pilha.
        # Chama `pdf.saveState` para executa a operacao do objeto com os argumentos indicados.
        pdf.saveState()
        # Chama `pdf.setStrokeColorRGB` para executa a operacao do objeto com os argumentos indicados.
        pdf.setStrokeColorRGB(0.68, 0.68, 0.68)
        # Chama `pdf.setLineWidth` para executa a operacao do objeto com os argumentos indicados.
        pdf.setLineWidth(0.45)
        # Chama `pdf.setDash` para executa a operacao do objeto com os argumentos indicados.
        pdf.setDash()
        # Percorre column in range(3) e executa o bloco para cada item.
        for column in range(3):
            # x recebe o valor que armazena em `x` o valor obtido de `left + column * VOLANTE_PRINT_WIDTH`.
            x = left + column * VOLANTE_PRINT_WIDTH
            # Chama `pdf.line` para desenha uma linha guia de corte no PDF.
            pdf.line(x, bottom, x, bottom + grid_height)
        # Percorre row in range(3) e executa o bloco para cada item.
        for row in range(3):
            # y recebe o valor que armazena em `y` o valor obtido de `bottom + row * VOLANTE_PRINT_HEIGHT`.
            y = bottom + row * VOLANTE_PRINT_HEIGHT
            # Chama `pdf.line` para desenha uma linha guia de corte no PDF.
            pdf.line(left, y, left + grid_width, y)
        # Chama `pdf.restoreState` para executa a operacao do objeto com os argumentos indicados.
        pdf.restoreState()
        # Chama `pdf.showPage` para finaliza a pagina atual do documento PDF.
        pdf.showPage()

    # Chama `pdf.save` para fecha e grava o documento PDF no buffer.
    pdf.save()
    # Devolve output.getvalue() ao codigo que chamou esta funcao.
    return output.getvalue()


# Gera uma pagina PDF no tamanho fisico da cartela contendo somente as marcacoes.
def build_direct_print_pdf(games: list[list[int]], offset_x_mm: float = 0.0, offset_y_mm: float = 0.0) -> bytes:
    # Cria um buffer em memoria para guardar o documento PDF.
    output = BytesIO()
    # Converte a largura fisica da cartela de pontos de referencia da imagem para pontos PDF.
    scale_x = VOLANTE_PRINT_WIDTH / VOLANTE_IMAGE_SIZE[0]
    # Converte a altura fisica da cartela de pontos de referencia da imagem para pontos PDF.
    scale_y = VOLANTE_PRINT_HEIGHT / VOLANTE_IMAGE_SIZE[1]
    # Converte o ajuste horizontal de milimetros para pontos PDF.
    offset_x = offset_x_mm * 72 / 25.4
    # Converte o ajuste vertical de milimetros para pontos PDF.
    offset_y = offset_y_mm * 72 / 25.4
    # Cria um documento com uma pagina do tamanho exato de uma cartela.
    pdf = canvas.Canvas(output, pagesize=(VOLANTE_PRINT_WIDTH, VOLANTE_PRINT_HEIGHT))
    # Agrupa jogos de mesmo tamanho em cartelas com ate tres jogos.
    cards = group_print_cards(games)
    # Percorre cada cartela que precisa ser impressa individualmente.
    for game_size, card_games in cards:
        # Define preto solido para desenhar apenas as marcacoes solicitadas.
        pdf.setFillColorRGB(0, 0, 0)
        # Percorre os jogos posicionados nas tres areas disponiveis da cartela.
        for board_index, game in enumerate(card_games):
            # Percorre cada dezena do jogo sem repetir marcacoes.
            for number in set(game):
                # Desenha o quadrado preto da dezena na escala da cartela fisica.
                draw_volante_mark(pdf, volante_mark_position(board_index, number), scale_x, scale_y, offset_x=offset_x, offset_y=offset_y)
        # Verifica que o tamanho selecionado corresponde a uma opcao permitida.
        if game_size in BET_PRICES:
            # Desenha a marcacao preta de 15 a 20 dezenas.
            draw_volante_mark(pdf, volante_size_mark_position(game_size), scale_x, scale_y, offset_x=offset_x, offset_y=offset_y)
        # Finaliza a pagina da cartela para que a impressora avance ao proximo volante.
        pdf.showPage()
    # Grava o documento PDF no buffer.
    pdf.save()
    # Devolve os bytes do PDF para o botao de download.
    return output.getvalue()


# Gera uma cartela de calibracao com casas de referencia e regua de escala.
def build_calibration_pdf(offset_x_mm: float = 0.0, offset_y_mm: float = 0.0) -> bytes:
    # Cria um buffer em memoria para o PDF de calibracao.
    output = BytesIO()
    # Calcula a escala horizontal do recorte para a cartela fisica.
    scale_x = VOLANTE_PRINT_WIDTH / VOLANTE_IMAGE_SIZE[0]
    # Calcula a escala vertical do recorte para a cartela fisica.
    scale_y = VOLANTE_PRINT_HEIGHT / VOLANTE_IMAGE_SIZE[1]
    # Converte o deslocamento horizontal informado em pontos PDF.
    offset_x = offset_x_mm * 72 / 25.4
    # Converte o deslocamento vertical informado em pontos PDF.
    offset_y = offset_y_mm * 72 / 25.4
    # Cria uma pagina do tamanho fisico de uma cartela individual.
    pdf = canvas.Canvas(output, pagesize=(VOLANTE_PRINT_WIDTH, VOLANTE_PRINT_HEIGHT))
    # Seleciona preto para as casas de referencia da cartela.
    pdf.setFillColorRGB(0, 0, 0)
    # Usa quatro dezenas nos extremos e uma no centro para conferir alinhamento.
    for number in (1, 5, 13, 21, 25):
        # Imprime a casa de referencia na escala e deslocamento configurados.
        draw_volante_mark(pdf, volante_mark_position(0, number), scale_x, scale_y, offset_x=offset_x, offset_y=offset_y)
    # Marca a opcao de quinze dezenas como referencia para alinhamento.
    draw_volante_mark(pdf, volante_size_mark_position(15), scale_x, scale_y, offset_x=offset_x, offset_y=offset_y)
    # Define uma cor cinza escura para a regua que verifica a escala de impressao.
    pdf.setStrokeColorRGB(0.25, 0.25, 0.25)
    # Define a espessura da regua em pontos PDF.
    pdf.setLineWidth(0.6)
    # Posiciona a regua proximo da borda inferior da pagina de calibracao.
    ruler_y = VOLANTE_PRINT_HEIGHT * 0.08
    # Define o inicio horizontal da regua com uma pequena margem.
    ruler_x = 12
    # Converte 50 milimetros para pontos PDF.
    ruler_length = 50 * 72 / 25.4
    # Desenha a linha horizontal de cinquenta milimetros.
    pdf.line(ruler_x, ruler_y, ruler_x + ruler_length, ruler_y)
    # Desenha a marca vertical no inicio da regua.
    pdf.line(ruler_x, ruler_y - 4, ruler_x, ruler_y + 4)
    # Desenha a marca vertical no final da regua.
    pdf.line(ruler_x + ruler_length, ruler_y - 4, ruler_x + ruler_length, ruler_y + 4)
    # Define uma fonte pequena para a identificacao da medida.
    pdf.setFont("Helvetica", 7)
    # Imprime a medida nominal para comparar com uma regua fisica.
    pdf.drawString(ruler_x, ruler_y + 5, "50 mm - imprimir a 100%")
    # Finaliza a unica pagina do arquivo de calibracao.
    pdf.showPage()
    # Grava o documento PDF no buffer.
    pdf.save()
    # Devolve o arquivo de calibracao para o download.
    return output.getvalue()

# Renderiza o modulo de geracao por grupos configuraveis.
def render_group_generator() -> None:
    # Identifica a funcao desta area.
    st.subheader("Gerador por Grupos")
    # Explica como as cores da planilha sao representadas neste modulo.
    st.caption("Selecione as dezenas que participam de cada grupo e quantas entram em cada jogo.")
    # Usa os cinco intervalos de dezenas definidos nas constantes do modulo.
    ranges = GROUP_RANGES
    # Usa as quantidades iniciais definidas nas constantes do modulo.
    default_picks = GROUP_DEFAULT_PICKS
    # Cria cinco colunas para exibir os grupos lado a lado.
    group_columns = st.columns(5)
    # Inicia a configuracao que sera usada pela geracao de combinacoes.
    configured_groups = []
    # Percorre cada grupo e seus controles de selecao.
    for group_index, (group_range, default_pick, group_column) in enumerate(zip(ranges, default_picks, group_columns)):
        # Mostra os limites do intervalo armazenado como uma tupla de dezenas.
        group_column.markdown(f"**Grupo {group_index + 1}**  \n{group_range[0]:02d}–{group_range[-1]:02d}")
        # Prepara a selecao das dezenas deste grupo.
        selected_numbers = []
        # Adiciona por padrao somente a dezena 3 no primeiro grupo e todas nas demais faixas.
        for number in group_range:
            # Define se a dezena deve iniciar selecionada.
            default_selected = number in GROUP_DEFAULT_SELECTED_NUMBERS
            # Cria uma caixa de selecao para a dezena.
            if group_column.checkbox(f"{number:02d}", value=default_selected, key=f"group_number_{number}"):
                # Guarda a dezena marcada para formar as combinacoes.
                selected_numbers.append(number)
        # Corrige o valor previamente salvo se a selecao do grupo foi reduzida.
        pick_key = f"group_pick_{group_index}"
        # Limita a quantidade salva ao numero de dezenas selecionadas.
        if st.session_state.get(pick_key, default_pick) > len(selected_numbers):
            # Atualiza o estado para manter o controle dentro do limite permitido.
            st.session_state[pick_key] = len(selected_numbers)
        # Cria o seletor da quantidade a escolher dentro do grupo.
        pick = group_column.number_input("Quantidade", min_value=0, max_value=len(selected_numbers), value=min(default_pick, len(selected_numbers)), step=1, key=pick_key)
        # Adiciona o grupo a configuracao quando ha dezenas a escolher.
        if selected_numbers and pick:
            # Armazena dezenas disponiveis e quantidade para a funcao combinatoria.
            configured_groups.append((selected_numbers, int(pick)))
    # Salva a configuracao para uso pelo callback de geracao.
    st.session_state["group_generation_config"] = configured_groups
    # Calcula quantas dezenas tera cada jogo.
    total_numbers = sum(pick for _, pick in configured_groups)
    # Apresenta a quantidade total de dezenas por aposta.
    st.metric("Dezenas por jogo", total_numbers)
    # Calcula a quantidade de combinacoes que a configuracao atual produziria.
    total_combinations = expected_combination_count(configured_groups)
    # Mostra a previsao para o usuario antes de iniciar a geracao.
    st.metric("Combinações previstas", f"{total_combinations:,}".replace(",", "."))
    # Identifica configuracoes que ultrapassam o limite de geracao em memoria.
    exceeds_limit = total_combinations > MAX_GENERATED_GAMES
    # Explica o limite antes de o usuario acionar o botao.
    if exceeds_limit:
        # Informa o total estimado e o limite aceito.
        st.warning(f"A configuração excede o limite de {MAX_GENERATED_GAMES:,} combinações.".replace(",", "."))
    # Valida o total exigido pelas regras da Lotofacil.
    if total_numbers and not 15 <= total_numbers <= 20:
        # Orienta o usuario a ajustar as quantidades.
        st.warning("A soma das quantidades dos grupos deve ficar entre 15 e 20 dezenas.")
    # Cria botoes para gerar, conferir e imprimir as combinacoes.
    generate_col, checker_col, print_col = st.columns(3)
    # Dispara a geracao das combinacoes dos grupos.
    generate_col.button("Gerar combinações", type="primary", use_container_width=True, on_click=generate_group_games, disabled=exceeds_limit)
    # Navega ao conferidor com as combinacoes geradas.
    checker_col.button("Conferir jogos gerados", use_container_width=True, on_click=open_group_games_in_checker)
    # Navega ao impressor com as combinacoes geradas.
    print_col.button("Enviar para imprimir", use_container_width=True, on_click=open_group_games_in_printer)
    # Recupera e remove um eventual aviso deixado por um callback.
    generation_error = st.session_state.pop("group_generation_error", None)
    # Exibe avisos produzidos pelos botoes de encaminhamento.
    if generation_error:
        # Mostra o motivo pelo qual a acao nao pode continuar.
        st.warning(generation_error)
    # Exibe as combinacoes quando ja houver resultado armazenado.
    games = st.session_state.get("group_generated_games", [])
    # Mostra um resumo e uma amostra dos jogos gerados.
    if games:
        # Informa quantas combinacoes foram produzidas.
        st.success(f"{len(games):,} combinação(ões) gerada(s).".replace(",", "."))
        # Apresenta ate dez jogos para conferencia visual.
        for game in games[:10]:
            # Mostra um jogo formatado como texto.
            st.code(format_game(game), language="text")
        # Permite baixar o conjunto completo em arquivo texto.
        st.download_button("Baixar combinações (.txt)", data=st.session_state["group_generated_games_txt"], file_name="combinacoes_por_grupo.txt", mime="text/plain", use_container_width=True)


# Renderiza a interface do gerador de combinacoes Lotofacil.
def render_generator():
    # Chama `st.subheader` para executa a operacao do objeto com os argumentos indicados.
    st.subheader("Gerador de Combinações")
    # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
    st.caption("Marque as dezenas no volante interativo: 1º clique fixa a dezena (vinho), 2º clique torna variável (azul) e 3º clique remove.")

    # fixed, variables, order recebe o valor que armazena em `fixed` o valor obtido de `render_unified_ticket("main_ticket")`.
    fixed, variables, order = render_unified_ticket("main_ticket")
    
    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown("---")
    # variable_pick recebe o valor que armazena em `variable_pick` o valor obtido de `st.number_input(`.
    variable_pick = st.number_input(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        "Quantas dezenas variáveis entram em cada cartela gerada?",
        # min_value recebe o valor que armazena em `min_value` o valor obtido de `0,`.
        min_value=0,
        # max_value recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
        max_value=len(variables),
        # value recebe o valor que armazena em `value` o valor obtido de `min(1, len(variables)) if variables else 0,`.
        value=min(1, len(variables)) if variables else 0,
        # step recebe o valor que armazena em `step` o valor obtido de `1,`.
        step=1,
        # help recebe o valor que define o texto ou identificador `"As combinações serão geradas escolhendo essa` usado nesta etapa.
        help="As combinações serão geradas escolhendo essa quantidade entre as dezenas azuis.",
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )

    # configured_count recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
    configured_count = len(fixed) + int(variable_pick)
    # combination_count recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
    combination_count = math.comb(len(variables), int(variable_pick)) if variables else (1 if fixed else 0)
    # Identifica combinacoes acima do limite de memoria antes de habilitar a geracao.
    exceeds_game_limit = combination_count > MAX_GENERATED_GAMES
    
    # first_metric, second_metric recebe o valor que cria as colunas da interface usadas para organizar os controles.
    first_metric, second_metric = st.columns(2)
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    first_metric.metric("Dezenas por Cartela", configured_count)
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    second_metric.metric("Combinações Previstas", f"{combination_count:,}".replace(",", "."))
    # Explica por que combinacoes muito grandes nao podem ser geradas nesta sessao.
    if exceeds_game_limit:
        # Mostra o limite de seguranca aplicado ao gerador.
        st.error(f"O total excede o limite de {MAX_GENERATED_GAMES:,} combinações por geração.".replace(",", "."))

    # Verifica se `configured_count and not 15 <= configured_count <= 20`.
    if configured_count and not 15 <= configured_count <= 20:
        # Chama `st.warning` para mostra um alerta de atencao.
        st.warning("Uma aposta Lotofácil válida deve ter entre 15 e 20 dezenas por cartela.")

    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown("---")
    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown("#### Filtros Avançados")
    # enable_sequence_filter recebe o valor que armazena em `enable_sequence_filter` o valor obtido de `st.checkbox("Filtrar por sequência de números", key="main_enable_`.
    enable_sequence_filter = st.checkbox("Filtrar por sequência de números", key="main_enable_seq")
    # sequence_limit recebe o valor que armazena em `sequence_limit` o valor obtido de `0`.
    sequence_limit = 0
    # Verifica se `enable_sequence_filter`.
    if enable_sequence_filter:
        # sequence_limit recebe o valor que armazena em `sequence_limit` o valor obtido de `st.number_input(`.
        sequence_limit = st.number_input(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            "Eliminar jogos que tenham uma sequência de pelo menos (dezenas):",
            # min_value recebe o valor que armazena em `min_value` o valor obtido de `2,`.
            min_value=2,
            # max_value recebe o valor que armazena em `max_value` o valor obtido de `15,`.
            max_value=15,
            # value recebe o valor que armazena em `value` o valor obtido de `3,`.
            value=3,
            # step recebe o valor que armazena em `step` o valor obtido de `1,`.
            step=1,
            # key recebe o valor que define o texto ou identificador `"main_seq_limit",` usado nesta etapa.
            key="main_seq_limit",
            # help recebe o valor que define o texto ou identificador `"Se 3 for escolhido, jogos contendo 1,2,3 ou ` usado nesta etapa.
            help="Se 3 for escolhido, jogos contendo 1,2,3 ou 5,6,7 serão eliminados."
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown("<br>", unsafe_allow_html=True)
    # generate_column, checker_column recebe o valor que cria as colunas da interface usadas para organizar os controles.
    generate_column, checker_column = st.columns(2)
    # generate_clicked recebe o valor que armazena em `generate_clicked` o valor obtido de `generate_column.button("⚡ Gerar Combinações", type="primary", use`.
    generate_clicked = generate_column.button("⚡ Gerar Combinações", type="primary", use_container_width=True, disabled=exceeds_game_limit)
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    checker_column.button(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        "🔍 Conferir Jogos Gerados", use_container_width=True,
        # help recebe o valor que define o texto ou identificador `"Abre o conferidor, carrega os jogos gerados ` usado nesta etapa.
        help="Abre o conferidor, carrega os jogos gerados e busca os últimos resultados.",
        # on_click recebe o valor que armazena em `on_click` o valor obtido de `open_generated_games_in_checker,`.
        on_click=open_generated_games_in_checker,
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )
    # Verifica se `st.session_state.pop("checker_navigation_error", False)`.
    if st.session_state.pop("checker_navigation_error", False):
        # Chama `st.warning` para mostra um alerta de atencao.
        st.warning("Gere as combinações antes de enviá-las ao conferidor.")

    # Verifica se `generate_clicked`.
    if generate_clicked:
        # Verifica se `not fixed and not variables`.
        if not fixed and not variables:
            # Chama `st.error` para mostra uma mensagem de erro.
            st.error("Marque pelo menos uma dezena na cartela.")
            # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
            return
        # Verifica se `not variables and fixed`.
        if not variables and fixed:
            # variable_pick recebe o valor que armazena em `variable_pick` o valor obtido de `0`.
            variable_pick = 0
        # Inicia um bloco protegido para tratar possiveis falhas da operacao.
        try:
            # games recebe o valor que armazena em `games` o valor obtido de `generate_ticket_combinations(fixed, variables, int(variable_pick)`.
            games = generate_ticket_combinations(fixed, variables, int(variable_pick), order)
            # Verifica se `enable_sequence_filter and sequence_limit > 0`.
            if enable_sequence_filter and sequence_limit > 0:
                # games recebe o valor que armazena em `games` o valor obtido de `filter_games_by_sequence(games, sequence_limit, fixed=fixed)`.
                games = filter_games_by_sequence(games, sequence_limit, fixed=fixed)
        # Trata a excecao indicada para permitir uma resposta controlada ao erro.
        except ValueError as exc:
            # Chama `st.error` para mostra uma mensagem de erro.
            st.error(str(exc))
            # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
            return
        # Verifica se `not games`.
        if not games:
            # Chama `st.warning` para mostra um alerta de atencao.
            st.warning("Nenhuma combinação gerada, ou todas foram filtradas.")
            # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
            return
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        st.session_state["generated_games"] = games
        # Chama `st.session_state["generated_games_txt"] = "\n".join` para executa a operacao do objeto com os argumentos indicados.
        st.session_state["generated_games_txt"] = "\n".join(format_game(game) for game in games)
        # Chama `st.success` para confirma a conclusao de uma operacao.
        st.success(f"🎉 {len(games):,} combinação(ões) gerada(s) com sucesso!".replace(",", "."))

    # Verifica se `st.session_state.get("generated_games")`.
    if st.session_state.get("generated_games"):
        # games recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
        games = st.session_state["generated_games"]
        # Chama `st.info` para mostra uma mensagem informativa.
        st.info(f"✨ **{len(games):,}** jogos prontos para download.".replace(",", "."))
        # unique_sizes recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
        unique_sizes = sorted({len(game) for game in games})
        # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
        st.caption("Dezenas por jogo: " + ", ".join(str(size) for size in unique_sizes))
        # preview_count recebe o valor que armazena em `preview_count` o valor obtido de `min(10, len(games))`.
        preview_count = min(10, len(games))
        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown(f"**Prévia** (primeiros {preview_count} de {len(games)} jogos):")
        # Percorre game in games[:preview_count] e executa o bloco para cada item.
        for game in games[:preview_count]:
            # st.code(format_game(game), language recebe o valor que define o texto ou identificador `"text")` usado nesta etapa.
            st.code(format_game(game), language="text")
            
        # Chama `st.download_button` para cria um botao para baixar o arquivo gerado.
        st.download_button(
            # label recebe o valor que define o texto ou identificador `"Baixar todos os jogos (.txt)",` usado nesta etapa.
            label="Baixar todos os jogos (.txt)",
            # data recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
            data=st.session_state["generated_games_txt"],
            # file_name recebe o valor que define o texto ou identificador `"jogos_lotofacil.txt",` usado nesta etapa.
            file_name="jogos_lotofacil.txt",
            # mime recebe o valor que define o texto ou identificador `"text/plain",` usado nesta etapa.
            mime="text/plain",
            # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
            use_container_width=True,
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )


# Renderiza os controles e o resumo de um grupo do modulo A/B/C.
def render_intersection_group(letter: str) -> None:
    # state_prefix recebe o valor que define o texto ou identificador `f"intersection_{letter.lower()}"` usado nesta etapa.
    state_prefix = f"intersection_{letter.lower()}"
    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown(f"### Arquivo {letter}")
    # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
    st.caption("1º clique = fixa (vinho); 2º clique = variável (azul).")
    # fixed, variables, order recebe o valor que armazena em `fixed` o valor obtido de `render_unified_ticket(f"{state_prefix}_ticket")`.
    fixed, variables, order = render_unified_ticket(f"{state_prefix}_ticket")
    # pick recebe o valor que armazena em `pick` o valor obtido de `st.number_input(`.
    pick = st.number_input(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        f"Variáveis por jogo do Arquivo {letter}",
        # min_value recebe o valor que armazena em `min_value` o valor obtido de `0,`.
        min_value=0,
        # max_value recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
        max_value=len(variables),
        # value recebe o valor que armazena em `value` o valor obtido de `min(1, len(variables)) if variables else 0,`.
        value=min(1, len(variables)) if variables else 0,
        # key recebe o valor que define o texto ou identificador `f"{state_prefix}_pick",` usado nesta etapa.
        key=f"{state_prefix}_pick",
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )
    # total recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
    total = len(fixed) + int(pick)
    # count recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
    count = math.comb(len(variables), int(pick)) if variables else (1 if fixed else 0)
    # Identifica geracoes acima do limite de combinacoes configurado.
    exceeds_game_limit = count > MAX_GENERATED_GAMES
    # metric_a, metric_b recebe o valor que cria as colunas da interface usadas para organizar os controles.
    metric_a, metric_b = st.columns(2)
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    metric_a.metric("Dezenas por Aposta", total)
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    metric_b.metric("Jogos Previstos", f"{count:,}".replace(",", "."))
    # Mostra um aviso antes de tentar gerar um arquivo grande.
    if exceeds_game_limit:
        # Informa o limite que impede a alocacao de combinacoes excessivas.
        st.warning(f"O Arquivo {letter} excede o limite de {MAX_GENERATED_GAMES:,} jogos.".replace(",", "."))
    # Verifica se `total and total not in BET_PRICES`.
    if total and total not in BET_PRICES:
        # Chama `st.warning` para mostra um alerta de atencao.
        st.warning("Cada jogo de A ou B deve ter de 15 a 20 dezenas.")

    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown("##### Filtro")
    # enable_sequence_filter recebe o valor que armazena em `enable_sequence_filter` o valor obtido de `st.checkbox(f"Filtrar por sequência de números (Arquivo {letter})`.
    enable_sequence_filter = st.checkbox(f"Filtrar por sequência de números (Arquivo {letter})", key=f"{state_prefix}_enable_seq")
    # sequence_limit recebe o valor que armazena em `sequence_limit` o valor obtido de `0`.
    sequence_limit = 0
    # Verifica se `enable_sequence_filter`.
    if enable_sequence_filter:
        # sequence_limit recebe o valor que armazena em `sequence_limit` o valor obtido de `st.number_input(`.
        sequence_limit = st.number_input(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            "Tamanho máximo de dezenas consecutivas:",
            # min_value recebe o valor que armazena em `min_value` o valor obtido de `2,`.
            min_value=2,
            # max_value recebe o valor que armazena em `max_value` o valor obtido de `15,`.
            max_value=15,
            # value recebe o valor que armazena em `value` o valor obtido de `3,`.
            value=3,
            # step recebe o valor que armazena em `step` o valor obtido de `1,`.
            step=1,
            # key recebe o valor que define o texto ou identificador `f"{state_prefix}_seq_limit",` usado nesta etapa.
            key=f"{state_prefix}_seq_limit",
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

    # Verifica se `st.button(f"🚀 Gerar Arquivo {letter}", key=f"generate_{state_prefix}", type="primary")`.
    if st.button(f"🚀 Gerar Arquivo {letter}", key=f"generate_{state_prefix}", type="primary", disabled=exceeds_game_limit):
        # Verifica se `total not in BET_PRICES`.
        if total not in BET_PRICES:
            # Chama `st.error` para mostra uma mensagem de erro.
            st.error("Configure de 15 a 20 dezenas por jogo antes de gerar.")
        # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
        else:
            # Tenta criar jogos respeitando limites e selecoes nao sobrepostas.
            try:
                # Gera o Arquivo A ou B com os parametros definidos pelo usuario.
                games = generate_ticket_combinations(fixed, variables, int(pick), order)
            # Exibe problemas de configuracao sem interromper o aplicativo.
            except ValueError as exc:
                # Apresenta o motivo pelo qual o arquivo nao pode ser gerado.
                st.error(str(exc))
                # Limpa jogos anteriores para evitar que parecam ser o resultado novo.
                st.session_state[f"{state_prefix}_games"] = []
                # Encerra a secao atual sem executar filtros sobre dados antigos.
                return
            # Verifica se `enable_sequence_filter and sequence_limit > 0`.
            if enable_sequence_filter and sequence_limit > 0:
                # games recebe o valor que armazena em `games` o valor obtido de `filter_games_by_sequence(games, sequence_limit, fixed=fixed)`.
                games = filter_games_by_sequence(games, sequence_limit, fixed=fixed)
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            st.session_state[f"{state_prefix}_games"] = games
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            st.session_state[f"{state_prefix}_fixed"] = fixed
            # Verifica se `not games`.
            if not games:
                # Chama `st.warning` para mostra um alerta de atencao.
                st.warning(f"O Arquivo {letter} não gerou jogos (ou todos foram filtrados).")
            # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
            else:
                # Chama `st.success` para confirma a conclusao de uma operacao.
                st.success(f"Arquivo {letter} gerado com {len(games):,} jogo(s).".replace(",", "."))

    # games recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    games = st.session_state.get(f"{state_prefix}_games", [])
    # Verifica se `games`.
    if games:
        # download_col, checker_col recebe o valor que cria as colunas da interface usadas para organizar os controles.
        download_col, checker_col = st.columns(2)
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        download_col.download_button(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            f"📄 Baixar Arquivo {letter} (.txt)",
            # data recebe o valor que define o texto ou identificador `"\n".join(format_game(game) for game in games` usado nesta etapa.
            data="\n".join(format_game(game) for game in games),
            # file_name recebe o valor que define o texto ou identificador `f"arquivo_{letter.lower()}_lotofacil.txt",` usado nesta etapa.
            file_name=f"arquivo_{letter.lower()}_lotofacil.txt",
            # mime recebe o valor que define o texto ou identificador `"text/plain",` usado nesta etapa.
            mime="text/plain",
            # key recebe o valor que define o texto ou identificador `f"download_{state_prefix}",` usado nesta etapa.
            key=f"download_{state_prefix}",
            # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
            use_container_width=True,
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        checker_col.button(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            f"🔍 Conferir Jogos do Arquivo {letter}",
            # key recebe o valor que define o texto ou identificador `f"checker_{state_prefix}",` usado nesta etapa.
            key=f"checker_{state_prefix}",
            # on_click recebe o valor que armazena em `on_click` o valor obtido de `make_open_intersection_ab_in_checker(letter),`.
            on_click=make_open_intersection_ab_in_checker(letter),
            # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
            use_container_width=True,
            # help recebe o valor que define o texto ou identificador `"Abre o conferidor com os jogos do Arquivo {}` usado nesta etapa.
            help="Abre o conferidor com os jogos do Arquivo {}, busca os últimos resultados automaticamente.".format(letter),
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )
        # Verifica se `st.session_state.pop("checker_navigation_error", False)`.
        if st.session_state.pop("checker_navigation_error", False):
            # Chama `st.warning` para mostra um alerta de atencao.
            st.warning(f"Gere o Arquivo {letter} antes de enviá-lo ao conferidor.")


# Renderiza e processa os grupos de dezenas do modulo A/B/C.
def render_intersection_module():
    # Chama `st.subheader` para executa a operacao do objeto com os argumentos indicados.
    st.subheader("Módulo A/B/C - Interseção & Variáveis Extras")
    # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
    st.caption("Gere os Arquivos A e B. No Passo 3, o sistema combina os miolos variáveis e acrescenta as dezenas extras escolhidas.")

    # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
    with st.expander("Passo 1 — Gerar Arquivo A", expanded=True):
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        render_intersection_group("A")
    # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
    with st.expander("Passo 2 — Gerar Arquivo B"):
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        render_intersection_group("B")
    # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
    with st.expander("Passo 3 — Gerar Arquivo C", expanded=True):
        # games_a recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
        games_a = st.session_state.get("intersection_a_games", [])
        # games_b recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
        games_b = st.session_state.get("intersection_b_games", [])
        # fixed_a recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
        fixed_a = st.session_state.get("intersection_a_fixed", [])
        # fixed_b recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
        fixed_b = st.session_state.get("intersection_b_fixed", [])
        # Verifica se `not games_a or not games_b`.
        if not games_a or not games_b:
            # Chama `st.info` para mostra uma mensagem informativa.
            st.info("💡 Gere os Arquivos A e B primeiro para habilitar a combinação do Arquivo C.")
            # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
            return

        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown("#### Dezenas Variáveis Extras (Opcional)")
        # extra_variables recebe o valor que armazena em `extra_variables` o valor obtido de `render_extra_ticket("intersection_extra_variables")`.
        extra_variables = render_extra_ticket("intersection_extra_variables")
        # target_size recebe o valor que armazena em `target_size` o valor obtido de `st.number_input(`.
        target_size = st.number_input(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            "Total de dezenas por aposta do Arquivo C",
            # min_value recebe o valor que armazena em `min_value` o valor obtido de `15,`.
            min_value=15,
            # max_value recebe o valor que armazena em `max_value` o valor obtido de `20,`.
            max_value=20,
            # value recebe o valor que armazena em `value` o valor obtido de `15,`.
            value=15,
            # step recebe o valor que armazena em `step` o valor obtido de `1,`.
            step=1,
            # key recebe o valor que define o texto ou identificador `"intersection_target_size",` usado nesta etapa.
            key="intersection_target_size",
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )
        # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
        st.caption(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            f"Miolo de A: sem {len(fixed_a)} fixa(s). Miolo de B: sem {len(fixed_b)} fixa(s). "
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            f"Extras selecionadas: {len(extra_variables)}."
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )

        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown("#### Filtro")
        # enable_sequence_filter recebe o valor que armazena em `enable_sequence_filter` o valor obtido de `st.checkbox("Filtrar por sequência de números (Arquivo C)", key="`.
        enable_sequence_filter = st.checkbox("Filtrar por sequência de números (Arquivo C)", key="intersection_c_enable_seq")
        # sequence_limit recebe o valor que armazena em `sequence_limit` o valor obtido de `0`.
        sequence_limit = 0
        # Verifica se `enable_sequence_filter`.
        if enable_sequence_filter:
            # sequence_limit recebe o valor que armazena em `sequence_limit` o valor obtido de `st.number_input(`.
            sequence_limit = st.number_input(
                # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                "Tamanho máximo de dezenas consecutivas:",
                # min_value recebe o valor que armazena em `min_value` o valor obtido de `2,`.
                min_value=2,
                # max_value recebe o valor que armazena em `max_value` o valor obtido de `15,`.
                max_value=15,
                # value recebe o valor que armazena em `value` o valor obtido de `3,`.
                value=3,
                # step recebe o valor que armazena em `step` o valor obtido de `1,`.
                step=1,
                # key recebe o valor que define o texto ou identificador `"intersection_c_seq_limit",` usado nesta etapa.
                key="intersection_c_seq_limit",
            # Fecha o agrupamento da chamada ou colecao iniciada acima.
            )

        # gen_col_c, check_col_c recebe o valor que cria as colunas da interface usadas para organizar os controles.
        gen_col_c, check_col_c = st.columns(2)
        # Verifica se `gen_col_c.button("✨ Gerar Arquivo C", type="primary", key="generate_intersection_c", use_container_width=True)`.
        if gen_col_c.button("✨ Gerar Arquivo C", type="primary", key="generate_intersection_c", use_container_width=True):
            # Tenta gerar apenas apostas completas sem ultrapassar os limites.
            try:
                # Combina os miolos de A e B com as dezenas extras disponiveis.
                games_c = generate_file_c(games_a, games_b, fixed_a, fixed_b, extra_variables, int(target_size))
            # Exibe falhas de configuracao ou excesso de volume sem derrubar a tela.
            except ValueError as exc:
                # Mostra a causa que impediu a geracao do Arquivo C.
                st.error(str(exc))
                # Remove qualquer resultado anterior que poderia confundir o usuario.
                st.session_state["intersection_c_games"] = []
                # Encerra o bloco antes de aplicar filtros ou exibir resultados antigos.
                return
            # Verifica se `enable_sequence_filter and sequence_limit > 0`.
            if enable_sequence_filter and sequence_limit > 0:
                # games_c recebe o valor que armazena em `games_c` o valor obtido de `filter_games_by_sequence(games_c, sequence_limit)`.
                games_c = filter_games_by_sequence(games_c, sequence_limit)

            # Verifica se `not games_c`.
            if not games_c:
                # Chama `st.error` para mostra uma mensagem de erro.
                st.error(
                    "Nenhum jogo gerado. Os miolos de A e B excedem o total, ou os filtros removeram tudo."
                # Fecha o agrupamento da chamada ou colecao iniciada acima.
                )
            # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
            else:
                # Compoe a expressao ou os argumentos da operacao iniciada acima.
                st.session_state["intersection_c_games"] = games_c
                # sizes recebe o valor que monta a colecao de valores usada pela etapa atual.
                sizes = [len(game) for game in games_c]
                # incomplete recebe o valor que monta a colecao de valores usada pela etapa atual.
                incomplete = [size for size in sizes if size < int(target_size)]
                # Verifica se `incomplete`.
                if incomplete:
                    # missing recebe o valor que armazena em `missing` o valor obtido de `max(int(target_size) - size for size in incomplete)`.
                    missing = max(int(target_size) - size for size in incomplete)
                    # Chama `st.warning` para mostra um alerta de atencao.
                    st.warning(
                        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                        f"Arquivo C gerado com a junção A+B, mas {len(incomplete)} jogo(s) ainda não atingem "
                        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                        f"{int(target_size)} dezenas. Faltam até {missing} dezena(s); selecione extras se quiser completá-los."
                    # Fecha o agrupamento da chamada ou colecao iniciada acima.
                    )
                # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
                else:
                    # Chama `st.success` para confirma a conclusao de uma operacao.
                    st.success(f"🎉 Arquivo C gerado com {len(games_c):,} jogo(s) de {int(target_size)} dezenas.".replace(",", "."))
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        check_col_c.button(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            "🔍 Conferir Jogos do Arquivo C",
            # key recebe o valor que define o texto ou identificador `"checker_intersection_c_quick",` usado nesta etapa.
            key="checker_intersection_c_quick",
            # on_click recebe o valor que armazena em `on_click` o valor obtido de `open_intersection_c_in_checker,`.
            on_click=open_intersection_c_in_checker,
            # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
            use_container_width=True,
            # help recebe o valor que define o texto ou identificador `"Abre o conferidor com os jogos do Arquivo C ` usado nesta etapa.
            help="Abre o conferidor com os jogos do Arquivo C e busca os últimos resultados automaticamente.",
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )
        # Verifica se `st.session_state.pop("checker_navigation_error", False)`.
        if st.session_state.pop("checker_navigation_error", False):
            # Chama `st.warning` para mostra um alerta de atencao.
            st.warning("Gere o Arquivo C antes de enviá-lo ao conferidor.")

        # games_c recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
        games_c = st.session_state.get("intersection_c_games", [])
        # Verifica se `games_c`.
        if games_c:
            # text_column, pdf_column, checker_column recebe o valor que cria as colunas da interface usadas para organizar os controles.
            text_column, pdf_column, checker_column = st.columns(3)
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            text_column.download_button(
                # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                "📄 Baixar Arquivo C (.txt)",
                # data recebe o valor que define o texto ou identificador `"\n".join(format_game(game) for game in games` usado nesta etapa.
                data="\n".join(format_game(game) for game in games_c),
                # file_name recebe o valor que define o texto ou identificador `"arquivo_c_lotofacil.txt",` usado nesta etapa.
                file_name="arquivo_c_lotofacil.txt",
                # mime recebe o valor que define o texto ou identificador `"text/plain",` usado nesta etapa.
                mime="text/plain",
                # key recebe o valor que define o texto ou identificador `"download_intersection_c",` usado nesta etapa.
                key="download_intersection_c",
                # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
                use_container_width=True,
            # Fecha o agrupamento da chamada ou colecao iniciada acima.
            )
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            pdf_column.download_button(
                # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                "🖨️ Baixar Arquivo C (.pdf)",
                # data recebe o valor que armazena em `data` o valor obtido de `build_games_pdf(games_c),`.
                data=build_games_pdf(games_c),
                # file_name recebe o valor que define o texto ou identificador `"arquivo_c_lotofacil_conferencia.pdf",` usado nesta etapa.
                file_name="arquivo_c_lotofacil_conferencia.pdf",
                # mime recebe o valor que define o texto ou identificador `"application/pdf",` usado nesta etapa.
                mime="application/pdf",
                # key recebe o valor que define o texto ou identificador `"download_intersection_c_pdf",` usado nesta etapa.
                key="download_intersection_c_pdf",
                # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
                use_container_width=True,
            # Fecha o agrupamento da chamada ou colecao iniciada acima.
            )
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            checker_column.button(
                # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
                "🔍 Conferir Arquivo C",
                # key recebe o valor que define o texto ou identificador `"checker_intersection_c",` usado nesta etapa.
                key="checker_intersection_c",
                # on_click recebe o valor que armazena em `on_click` o valor obtido de `open_intersection_c_in_checker,`.
                on_click=open_intersection_c_in_checker,
                # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
                use_container_width=True,
                # disabled recebe o valor que armazena em `disabled` o valor obtido de `any(len(game) not in BET_PRICES for game in games_c),`.
                disabled=any(len(game) not in BET_PRICES for game in games_c),
            # Fecha o agrupamento da chamada ou colecao iniciada acima.
            )
            # Verifica se `any(len(game) not in BET_PRICES for game in games_c)`.
            if any(len(game) not in BET_PRICES for game in games_c):
                # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
                st.caption("Complete as dezenas extras para habilitar a conferência do Arquivo C.")
            # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
            st.caption("Prévia do Arquivo C:")
            # Percorre game in games_c[:10] e executa o bloco para cada item.
            for game in games_c[:10]:
                # st.code(format_game(game), language recebe o valor que define o texto ou identificador `"text")` usado nesta etapa.
                st.code(format_game(game), language="text")


# Renderiza o conferidor e compara apostas com resultados de concursos.
def render_checker():
    # Chama `st.subheader` para executa a operacao do objeto com os argumentos indicados.
    st.subheader("Conferidor Oficial de Concursos")
    # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
    st.caption("Selecione no calendário as datas ou busque pelos últimos concursos. A premiação considera a tabela oficial da CAIXA.")

    # auto_check recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    auto_check = st.session_state.get("auto_check_pending", False)
    # Verifica se `auto_check`.
    if auto_check:
        # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
        with st.spinner("🔄 Buscando os 10 últimos concursos e conferindo os jogos..."):
            # Inicia um bloco protegido para tratar possiveis falhas da operacao.
            try:
                # Chama `st.session_state["calendar_results"] = fetch_recent_results` para executa a operacao do objeto com os argumentos indicados.
                st.session_state["calendar_results"] = fetch_recent_results(10)
                # Compoe a expressao ou os argumentos da operacao iniciada acima.
                st.session_state["checker_selected_contests"] = [
                    # Compoe a expressao ou os argumentos da operacao iniciada acima.
                    int(result["concurso"]) for result in st.session_state["calendar_results"]
                # Fecha o agrupamento da chamada ou colecao iniciada acima.
                ]
            # Trata a excecao indicada para permitir uma resposta controlada ao erro.
            except (requests.RequestException, ValueError) as exc:
                # Compoe a expressao ou os argumentos da operacao iniciada acima.
                st.session_state["auto_check_pending"] = False
                # Chama `st.error` para mostra uma mensagem de erro.
                st.error(f"Não foi possível consultar a API oficial da CAIXA. Verifique a conexão ou se o firewall/antivírus permite conexões HTTPS do Python. Detalhe: {exc}")
                # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
                return

    # today recebe o valor que armazena em `today` o valor obtido de `date.today()`.
    today = date.today()
    # selected_dates recebe o valor que armazena em `selected_dates` o valor obtido de `st.date_input(`.
    selected_dates = st.date_input(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        "📅 Calendário de Concursos",
        # value recebe o valor que monta a colecao de valores usada pela etapa atual.
        value=(today - timedelta(days=7), today),
        # max_value recebe o valor que armazena em `max_value` o valor obtido de `today,`.
        max_value=today,
        # format recebe o valor que define o texto ou identificador `"DD/MM/YYYY",` usado nesta etapa.
        format="DD/MM/YYYY",
        # help recebe o valor que define o texto ou identificador `"Selecione uma data ou período; o app busca o` usado nesta etapa.
        help="Selecione uma data ou período; o app busca os concursos realizados nele.",
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )
    # Verifica se `isinstance(selected_dates, tuple) and len(selected_dates) == 2`.
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        # start_date, end_date recebe o valor que armazena em `start_date` o valor obtido de `selected_dates`.
        start_date, end_date = selected_dates
    # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
    else:
        # start_date recebe o valor que armazena em `start_date` o valor obtido de `end_date = selected_dates`.
        start_date = end_date = selected_dates

    # Verifica se `start_date > end_date`.
    if start_date > end_date:
        # Chama `st.error` para mostra uma mensagem de erro.
        st.error("A data inicial deve ser anterior à final.")
        # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
        return
    # Verifica se `(end_date - start_date).days > 120`.
    if (end_date - start_date).days > 120:
        # Chama `st.warning` para mostra um alerta de atencao.
        st.warning("Para evitar muitas consultas, selecione até 120 dias.")
        # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
        return

    # Verifica se `st.button("🔍 Buscar Concursos no Calendário")`.
    if st.button("🔍 Buscar Concursos no Calendário"):
        # Abre o contexto indicado e garante o encerramento automatico ao sair do bloco.
        with st.spinner("Consultando resultados na API..."):
            # Inicia um bloco protegido para tratar possiveis falhas da operacao.
            try:
                # Chama `st.session_state["calendar_results"] = fetch_results_for_dates` para executa a operacao do objeto com os argumentos indicados.
                st.session_state["calendar_results"] = fetch_results_for_dates(start_date, end_date)
            # Trata a excecao indicada para permitir uma resposta controlada ao erro.
            except (requests.RequestException, ValueError) as exc:
                # Chama `st.error` para mostra uma mensagem de erro.
                st.error(f"Não foi possível consultar a API oficial da CAIXA. Verifique a conexão ou se o firewall/antivírus permite conexões HTTPS do Python. Detalhe: {exc}")
                # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
                return

    # found_results recebe o valor que le ou atualiza o estado da sessao para preservar a selecao entre interacoes.
    found_results = st.session_state.get("calendar_results", [])
    # result_by_contest recebe o valor que monta a colecao de valores usada pela etapa atual.
    result_by_contest = {int(item["concurso"]): item for item in found_results}
    # Verifica se `result_by_contest`.
    if result_by_contest:
        # selected_contests recebe o valor que armazena em `selected_contests` o valor obtido de `st.multiselect(`.
        selected_contests = st.multiselect(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            "Concursos a Conferir",
            # options recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
            options=list(result_by_contest),
            # default recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
            default=list(result_by_contest),
            # format_func recebe o valor que armazena em `format_func` o valor obtido de `lambda contest: f"Concurso {contest} — {result_by_contest[contest`.
            format_func=lambda contest: f"Concurso {contest} — {result_by_contest[contest]['data']}",
            # key recebe o valor que define o texto ou identificador `"checker_selected_contests",` usado nesta etapa.
            key="checker_selected_contests",
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )
        # Percorre contest in selected_contests e executa o bloco para cada item.
        for contest in selected_contests:
            # result recebe o valor que armazena em `result` o valor obtido de `result_by_contest[contest]`.
            result = result_by_contest[contest]
            # drawn recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
            drawn = sorted(int(d) for d in result["dezenas"])
            # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
            st.caption(f"📌 **Concurso {contest} ({result['data']})**: {', '.join(f'{d:02d}' for d in drawn)}")
    # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
    else:
        # selected_contests recebe o valor que monta a colecao de valores usada pela etapa atual.
        selected_contests = []

    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown("---")
    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown("**Seus Jogos**")
    # input_method recebe o valor que armazena em `input_method` o valor obtido de `st.radio(`.
    input_method = st.radio(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        "Como deseja enviar os jogos?", ["Colar texto", "Enviar arquivo .txt"],
        # horizontal recebe o valor que armazena em `horizontal` o valor obtido de `True, key="checker_input_method",`.
        horizontal=True, key="checker_input_method",
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )
    # games_text recebe o valor que define o texto ou identificador `""` usado nesta etapa.
    games_text = ""
    # Verifica se `input_method == "Colar texto"`.
    if input_method == "Colar texto":
        # games_text recebe o valor que armazena em `games_text` o valor obtido de `st.text_area(`.
        games_text = st.text_area(
            # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
            "Cole os jogos (um por linha)", height=180,
            # placeholder recebe o valor que define o texto ou identificador `"01,02,03,04,05,06,07,08,09,10,11,12,13,14,15` usado nesta etapa.
            placeholder="01,02,03,04,05,06,07,08,09,10,11,12,13,14,15",
            # key recebe o valor que define o texto ou identificador `"checker_games_text",` usado nesta etapa.
            key="checker_games_text",
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        )
    # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
    else:
        # uploaded recebe o valor que armazena em `uploaded` o valor obtido de `st.file_uploader("Arquivo .txt", type=["txt"])`.
        uploaded = st.file_uploader("Arquivo .txt", type=["txt"])
        # Verifica se `uploaded`.
        if uploaded:
            # Recupera o conteudo sem consumir permanentemente o cursor do upload.
            uploaded_bytes = uploaded.getvalue()
            # Tenta decodificar arquivos UTF-8 e remove eventual BOM do Bloco de Notas.
            try:
                # Decodifica primeiro no formato Unicode mais comum.
                games_text = uploaded_bytes.decode("utf-8-sig")
            # Interpreta arquivos Windows antigos usando a codificacao cp1252.
            except UnicodeDecodeError:
                # Decodifica bytes de arquivos ANSI sem falhar na leitura da tela.
                games_text = uploaded_bytes.decode("cp1252")

    # run_check recebe o valor que armazena em `run_check` o valor obtido de `st.button("🚀 Conferir Jogos", type="primary")`.
    run_check = st.button("🚀 Conferir Jogos", type="primary")
    # Verifica se `auto_check`.
    if auto_check:
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        st.session_state["auto_check_pending"] = False
        # run_check recebe o valor que armazena em `run_check` o valor obtido de `True`.
        run_check = True

    # Verifica se `run_check`.
    if run_check:
        # Verifica se `not selected_contests`.
        if not selected_contests:
            # Chama `st.warning` para mostra um alerta de atencao.
            st.warning("Busque e selecione pelo menos um concurso no calendário.")
            # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
            return
        # lines recebe o valor que armazena em `lines` o valor obtido de `games_text.strip().splitlines()`.
        lines = games_text.strip().splitlines()
        # Verifica se `not lines`.
        if not lines:
            # Chama `st.warning` para mostra um alerta de atencao.
            st.warning("Nenhum jogo informado.")
            # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
            return

        # games, invalid_lines recebe o valor que monta a colecao de valores usada pela etapa atual.
        games, invalid_lines = [], []
        # Percorre idx, line in enumerate(lines, start=1) e executa o bloco para cada item.
        for idx, line in enumerate(lines, start=1):
            # Interpreta a linha e transforma dezenas fora do intervalo em aviso localizado.
            try:
                # Le a aposta depois de remover rotulos e validar a faixa de dezenas.
                game = parse_game_line(line)
            # Trata entradas com dezenas que nao existem no volante.
            except ValueError as exc:
                # Guarda o problema com o numero da linha para o usuario corrigir.
                invalid_lines.append(f"Linha {idx}: {exc}")
                # Pula para a proxima linha sem incluir esta aposta na conferencia.
                continue
            # Verifica se `game is None`.
            if game is None:
                # Pula para a proxima repeticao do laco atual.
                continue
            # Verifica se `len(game) not in BET_PRICES`.
            if len(game) not in BET_PRICES:
                # Compoe a expressao ou os argumentos da operacao iniciada acima.
                invalid_lines.append(f"Linha {idx}: informe de 15 a 20 dezenas únicas.")
                # Pula para a proxima repeticao do laco atual.
                continue
            # Chama `games.append` para executa a operacao do objeto com os argumentos indicados.
            games.append(game)
        # Percorre message in invalid_lines e executa o bloco para cada item.
        for message in invalid_lines:
            # Chama `st.warning` para mostra um alerta de atencao.
            st.warning(message)
        # Verifica se `not games`.
        if not games:
            # Chama `st.warning` para mostra um alerta de atencao.
            st.warning("Nenhum jogo válido para conferir.")
            # Devolve o controle ao chamador sem valor ao codigo que chamou esta funcao.
            return

        # investment_per_contest recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
        investment_per_contest = sum(BET_PRICES[len(game)] for game in games)
        # total_investment recebe o valor que armazena em `total_investment` o valor obtido de `investment_per_contest * len(selected_contests)`.
        total_investment = investment_per_contest * len(selected_contests)
        # overall_units recebe o valor que monta a colecao de valores usada pela etapa atual.
        overall_units = {points: 0 for points in range(11, 16)}
        # total_received recebe o valor que armazena em `total_received` o valor obtido de `0.0`.
        total_received = 0.0
        # Define as colunas ordenadas do relatorio completo em CSV.
        result_columns = ["Concurso", "Data", "Jogo", "Dezenas", "Acertos", "Prêmios (11–15)", "Valor Recebido"]
        # Abre um buffer textual para compor o relatorio sem guardar cada linha como dicionario.
        csv_buffer = StringIO()
        # Cria um escritor CSV com cabecalho e colunas estaveis.
        csv_writer = csv.DictWriter(csv_buffer, fieldnames=result_columns)
        # Escreve o cabecalho uma vez antes de percorrer concursos e jogos.
        csv_writer.writeheader()
        # Mantem em memoria somente linhas premiadas para a tabela visivel.
        all_rows = []

        # Percorre contest in selected_contests e executa o bloco para cada item.
        for contest in selected_contests:
            # result recebe o valor que armazena em `result` o valor obtido de `result_by_contest[contest]`.
            result = result_by_contest[contest]
            # drawn_set recebe o valor que normaliza os dados para a estrutura exigida pelo restante do fluxo.
            drawn_set = set(int(d) for d in result["dezenas"])
            # contest_prizes recebe o valor que armazena em `contest_prizes` o valor obtido de `prizes_by_points(result)`.
            contest_prizes = prizes_by_points(result)
            # contest_units recebe o valor que monta a colecao de valores usada pela etapa atual.
            contest_units = {points: 0 for points in range(11, 16)}
            # contest_received recebe o valor que armazena em `contest_received` o valor obtido de `0.0`.
            contest_received = 0.0
            # Percorre game_index, game in enumerate(games, start=1) e executa o bloco para cada item.
            for game_index, game in enumerate(games, start=1):
                # hits recebe o valor que armazena em `hits` o valor obtido de `count_hits(game, drawn_set)`.
                hits = count_hits(game, drawn_set)
                # units recebe o valor que armazena em `units` o valor obtido de `prize_units(len(game), hits)`.
                units = prize_units(len(game), hits)
                # received recebe o valor que calcula o valor derivado dos dados usados nesta etapa.
                received = sum(units[p] * contest_prizes.get(p, 0) for p in units)
                # Atualiza `contest_received` com o resultado da operacao `+=` aplicada a `received`.
                contest_received += received
                # Percorre points in contest_units e executa o bloco para cada item.
                for points in contest_units:
                    # Atualiza `contest_units[points]` com o resultado da operacao `+=` aplicada a `units[points]`.
                    contest_units[points] += units[points]
                    # Atualiza `overall_units[points]` com o resultado da operacao `+=` aplicada a `units[points]`.
                    overall_units[points] += units[points]
                # Monta uma linha numerica que pode ser ordenada corretamente na tabela.
                result_row = {"Concurso": contest, "Data": result["data"], "Jogo": game_index, "Dezenas": len(game), "Acertos": hits, "Prêmios (11–15)": sum(units.values()), "Valor Recebido": received}
                # Escreve cada jogo e concurso no relatorio completo de CSV.
                csv_writer.writerow(result_row)
                # Guarda apenas apostas premiadas para limitar a memoria e a tabela.
                if result_row["Prêmios (11–15)"]:
                    # Adiciona a linha premiada para exibicao e ordenacao numerica.
                    all_rows.append(result_row)
            # Atualiza `total_received` com o resultado da operacao `+=` aplicada a `contest_received`.
            total_received += contest_received
            # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
            st.markdown(f"#### Concurso {contest} — {result['data']}")
            # columns recebe o valor que cria as colunas da interface usadas para organizar os controles.
            columns = st.columns(5)
            # Percorre index, points in enumerate(range(11, 16)) e executa o bloco para cada item.
            for index, points in enumerate(range(11, 16)):
                # Compoe a expressao ou os argumentos da operacao iniciada acima.
                columns[index].metric(f"{points} Pontos", contest_units[points])
            # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
            st.caption(f"💰 Recebido neste concurso: **{brl(contest_received)}**")

        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown("---")
        # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
        st.markdown("### 📊 Resumo Financeiro & Desempenho")
        # games_col, invested_col, prizes_col, balance_col recebe o valor que cria as colunas da interface usadas para organizar os controles.
        games_col, invested_col, prizes_col, balance_col = st.columns(4)
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        games_col.metric("Total de Jogos", len(games))
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        invested_col.metric("Investimento Total", brl(total_investment))
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        prizes_col.metric("Premiação Total", brl(total_received))
        
        # balance_val recebe o valor que armazena em `balance_val` o valor obtido de `total_received - total_investment`.
        balance_val = total_received - total_investment
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        balance_col.metric("Saldo Final", brl(balance_val), delta=f"{balance_val:+,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # columns recebe o valor que cria as colunas da interface usadas para organizar os controles.
        columns = st.columns(5)
        # Percorre index, points in enumerate(range(11, 16)) e executa o bloco para cada item.
        for index, points in enumerate(range(11, 16)):
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            columns[index].metric(f"Total {points} Pts", overall_units[points])

        # Usa somente apostas premiadas na tabela interativa compacta.
        winners = all_rows
        # Verifica se `winners`.
        if winners:
            # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
            st.markdown("#### 🏆 Jogos Premiados")
            # Mostra valores monetarios como numeros com formato brasileiro de moeda.
            st.dataframe(winners, use_container_width=True, hide_index=True, column_config={"Valor Recebido": st.column_config.NumberColumn("Valor Recebido", format="R$ %.2f")})
        # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
        else:
            # Chama `st.info` para mostra uma mensagem informativa.
            st.info("Nenhum prêmio de 11 a 15 pontos nos concursos selecionados.")
        # Identifica a secao que oferece o relatorio completo em arquivo.
        st.markdown("#### 📋 Relatório completo")
        # Explica que a tabela e compacta e que o CSV contem todas as linhas.
        st.caption(f"Tabela com {len(winners):,} resultado(s) premiado(s); o CSV inclui todos os {len(games) * len(selected_contests):,} pares de jogo e concurso.".replace(",", "."))
        # Baixa o relatorio completo, incluindo jogos sem premio.
        st.download_button("Baixar todos os resultados (.csv)", data=csv_buffer.getvalue(), file_name="resultados_conferencia_lotofacil.csv", mime="text/csv", use_container_width=True)



# Valida uma aposta por linha e reporta problemas de formato ou dezenas.
def parse_print_games(text: str) -> tuple[list[list[int]], list[str]]:
    """L\u00ea uma aposta v\u00e1lida da Lotof\u00e1cil por linha n\u00e3o vazia."""
    # games recebe o valor que monta a colecao de valores usada pela etapa atual.
    games = []
    # errors recebe o valor que monta a colecao de valores usada pela etapa atual.
    errors = []
    # Percorre line_number, line in enumerate(text.splitlines(), start=1) e executa o bloco para cada item.
    for line_number, line in enumerate(text.splitlines(), start=1):
        # Verifica se `not line.strip()`.
        if not line.strip():
            # Pula para a proxima repeticao do laco atual.
            continue
        # Retira rotulos e ignora dezenas fora de 1 a 25 conforme regra do impressor.
        numbers = [number for number in parse_numbers(strip_game_label(line)) if number in ALL_NUMBERS]
        # Verifica se `not numbers`.
        if not numbers:
            # Ignora linhas vazias ou que so contenham valores fora do intervalo valido.
            continue
        # Verifica se `len(numbers) != len(set(numbers))`.
        if len(numbers) != len(set(numbers)):
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            errors.append(f"Linha {line_number}: remova as dezenas repetidas.")
            # Pula para a proxima repeticao do laco atual.
            continue
        # Verifica se `len(numbers) not in BET_PRICES`.
        if len(numbers) not in BET_PRICES:
            # Compoe a expressao ou os argumentos da operacao iniciada acima.
            errors.append(f"Linha {line_number}: informe de 15 a 20 dezenas diferentes.")
            # Pula para a proxima repeticao do laco atual.
            continue
        # Chama `games.append` para executa a operacao do objeto com os argumentos indicados.
        games.append(sorted(numbers))
    # Devolve games, errors ao codigo que chamou esta funcao.
    return games, errors


# Renderiza a area de colagem de apostas e geracao da folha PDF.
def render_print_module() -> None:
    # Chama `st.subheader` para executa a operacao do objeto com os argumentos indicados.
    st.subheader("Imprimir Folha Loto")
    # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
    st.caption(
        "Cole uma aposta por linha. Separe as dezenas por espa\u00e7os, v\u00edrgulas ou outros sinais; "
        "cada linha deve conter de 15 a 20 dezenas diferentes, entre 01 e 25."
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )
    # games_text recebe o valor que armazena em `games_text` o valor obtido de `st.text_area(`.
    games_text = st.text_area(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        "Jogos para imprimir",
        # height recebe o valor que armazena em `height` o valor obtido de `220,`.
        height=220,
        # placeholder recebe o valor que monta a colecao de valores usada pela etapa atual.
        placeholder=(
            "01,02,03,04,05,06,07,08,09,10,11,12,13,14,15\n"
            "01 03 05 07 09 11 13 15 17 19 21 22 23 24 25"
        # Fecha o agrupamento da chamada ou colecao iniciada acima.
        ),
        # key recebe o valor que define o texto ou identificador `"print_games_text",` usado nesta etapa.
        key="print_games_text",
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )
    # games, errors recebe o valor que armazena em `games` o valor obtido de `parse_print_games(games_text)`.
    games, errors = parse_print_games(games_text)
    # Permite escolher a folha A4 atual ou a impressao direta em cartela avulsa.
    print_mode = st.radio("Formato de impressão", ["Folha A4 com scanner", "Impressão direta na cartela"], horizontal=True, key="print_mode")
    # Inicia os deslocamentos sem ajuste para o formato A4.
    offset_x_mm = 0.0
    # Inicia os deslocamentos verticais sem ajuste para o formato A4.
    offset_y_mm = 0.0
    # Exibe controles de alinhamento e calibracao exclusivos da impressao direta.
    if print_mode == "Impressão direta na cartela":
        # Cria colunas para os dois eixos de ajuste da impressora.
        offset_columns = st.columns(2)
        # Permite deslocar as marcacoes para a direita ou esquerda em milimetros.
        offset_x_mm = offset_columns[0].number_input("Ajuste horizontal (mm)", min_value=-5.0, max_value=5.0, value=0.0, step=0.1, key="print_offset_x_mm", help="Valores positivos movem as marcações para a direita.")
        # Permite deslocar as marcacoes para cima ou para baixo em milimetros.
        offset_y_mm = offset_columns[1].number_input("Ajuste vertical (mm)", min_value=-5.0, max_value=5.0, value=0.0, step=0.1, key="print_offset_y_mm", help="Valores positivos movem as marcações para cima.")
        # Orienta a calibracao da escala pela regua impressa.
        st.caption("Imprima primeiro em uma cartela de teste: a página inclui marcas de referência e uma régua de 50 mm para conferir alinhamento e escala.")
        # Cria e oferece a cartela de calibracao com os deslocamentos atuais.
        st.download_button("Baixar cartela de calibração", data=build_calibration_pdf(offset_x_mm, offset_y_mm), file_name="calibracao_impressora_loto.pdf", mime="application/pdf", use_container_width=True)
    # Verifica se `games`.
    if games:
        # count_column, page_column recebe o valor que cria as colunas da interface usadas para organizar os controles.
        count_column, page_column = st.columns(2)
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        count_column.metric("Jogos v\u00e1lidos", len(games))
        # Exibe a quantidade de paginas conforme o formato de impressao escolhido.
        if print_mode == "Impressão direta na cartela":
            # Conta cartelas fisicas individuais agrupando jogos de tamanho igual.
            page_column.metric("Cartelas para alimentar", len(group_print_cards(games)))
        # Exibe o total de paginas A4 no formato com scanner.
        else:
            # Mantem a contagem de paginas do layout A4 existente.
            page_column.metric("Folhas A4", print_page_count(games))
        # Chama `st.caption` para mostra uma legenda auxiliar ao usuario.
        st.caption("Jogos com a mesma quantidade de dezenas ficam juntos no mesmo volante.")
        # Identifica jogos com quantidades diferentes de dezenas.
        if len({len(game) for game in games}) > 1:
            # Avisa que tamanhos distintos ficam em cartelas fisicas separadas.
            st.warning("Há jogos com quantidades diferentes de dezenas. Eles serão impressos em cartelas separadas para não compartilhar a marcação de tamanho.")
        # Explica como funciona a alimentacao da impressora no modo direto.
        if print_mode == "Impressão direta na cartela":
            # Informa o tamanho de pagina e que cada uma avanca uma cartela.
            st.caption("Cada página do PDF corresponde a uma cartela de 8,2 × 14 cm e contém até 3 jogos do mesmo tamanho.")
            # Orienta a configuracao fisica da impressora e a escala de saida.
            st.caption("Configure a impressora para a largura e altura da cartela e imprima em 100%, sem ajustar à página.")
            # Informa que o arquivo contem somente as casas preenchidas.
            st.caption("Este formato imprime apenas os quadrados pretos das dezenas e da quantidade de números; não inclui o scanner nem contornos.")
        # Mantem as instrucoes do formato A4 com imagem e guias de corte.
        else:
            # Informa a capacidade do layout A4 existente.
            st.caption("Cada folha A4 em retrato comporta 4 volantes, com até 12 jogos.")
            # Informa o tamanho real e o alinhamento das guias de corte.
            st.caption("As linhas cinza contornam cartelas de 8,2 x 14 cm e ficam alinhadas em todas as folhas para corte em pilha.")
            # Orienta a impressao em escala fisica correta.
            st.caption("Imprima em tamanho real (100%), sem ajustar à página.")
        # Chama `st.write` para exibe o valor ou resumo calculado na interface.
        st.write("Dezenas por linha: " + ", ".join(str(len(game)) for game in games))
    # Percorre error in errors e executa o bloco para cada item.
    for error in errors:
        # Chama `st.error` para mostra uma mensagem de erro.
        st.error(error)
    # Verifica se `not games and not errors`.
    if not games and not errors:
        # Chama `st.info` para mostra uma mensagem informativa.
        st.info("Cole os jogos acima para preparar o PDF.")
    # Gera o PDF no formato escolhido quando todas as linhas sao validas.
    pdf_data = build_direct_print_pdf(games, offset_x_mm, offset_y_mm) if games and not errors and print_mode == "Impressão direta na cartela" else build_games_pdf(games) if games and not errors else b""
    # Define o rotulo e o nome de arquivo para a modalidade escolhida.
    pdf_label = "Gerar PDF para impressão direta" if print_mode == "Impressão direta na cartela" else "Gerar PDF da Folha Loto"
    # Define o nome de arquivo correspondente ao formato selecionado.
    pdf_filename = "marcacoes_diretas_cartela.pdf" if print_mode == "Impressão direta na cartela" else "folha_loto.pdf"
    # Exibe uma previa da primeira pagina e a distribuicao dos jogos por tamanho.
    if games and not errors:
        # Reune as cartelas agrupadas para resumir a distribuicao da impressao.
        print_cards = group_print_cards(games)
        # Abre um painel que pode ser expandido para ver a previa do arquivo.
        with st.expander("Prévia do PDF e distribuição"):
            # Resume a quantidade de jogos em cada tamanho de aposta.
            for size in sorted({len(game) for game in games}):
                # Conta jogos daquele tamanho.
                games_of_size = sum(1 for game in games if len(game) == size)
                # Calcula quantas cartelas fisicas receberao esse tamanho.
                cards_of_size = math.ceil(games_of_size / 3)
                # Apresenta a distribuicao de jogos em cartelas para aquele tamanho.
                st.write(f"{size} dezenas: {games_of_size} jogo(s) em {cards_of_size} cartela(s).")
            # Escolhe a primeira cartela para o modo direto ou ate quatro no modo A4.
            preview_cards = print_cards[:1] if print_mode == "Impressão direta na cartela" else print_cards[:VOLANTES_PER_PAGE]
            # Converte as cartelas da primeira pagina em uma lista de jogos.
            preview_games = [game for _, card_games in preview_cards for game in card_games]
            # Gera somente a pagina de previa no formato selecionado.
            preview_pdf = build_direct_print_pdf(preview_games, offset_x_mm, offset_y_mm) if print_mode == "Impressão direta na cartela" else build_games_pdf(preview_games)
            # Codifica o PDF para incorporacao no visualizador da pagina.
            preview_encoded = base64.b64encode(preview_pdf).decode("ascii")
            # Exibe a primeira pagina em um leitor PDF incorporado.
            st.markdown(f'<iframe src="data:application/pdf;base64,{preview_encoded}" width="100%" height="640" style="border: 1px solid #ddd; border-radius: 8px;"></iframe>', unsafe_allow_html=True)
    # Cria o botao de download para o PDF do formato selecionado.
    st.download_button(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        pdf_label,
        # Envia os bytes do PDF gerado no modo de impressao selecionado.
        data=pdf_data,
        # Define o nome do arquivo conforme o formato de impressao selecionado.
        file_name=pdf_filename,
        # mime recebe o valor que define o texto ou identificador `"application/pdf",` usado nesta etapa.
        mime="application/pdf",
        # disabled recebe o valor que calcula a condicao `not games or bool(errors),` usada para decidir o fluxo.
        disabled=not games or bool(errors),
        # use_container_width recebe o valor que armazena em `use_container_width` o valor obtido de `True,`.
        use_container_width=True,
        # Explica o formato atual no texto de ajuda do botao.
        help="Gera as marcações sobre o scanner em A4 ou somente as marcações em páginas de 8,2 × 14 cm, conforme o formato escolhido.",
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )


# Configura a pagina, a navegacao e a secao ativa do aplicativo.
def main():
    # Chama `st.set_page_config` para executa a operacao do objeto com os argumentos indicados.
    st.set_page_config(
        # page_title recebe o valor que define o texto ou identificador `"Lotofácil Pro — Gerador & Conferidor",` usado nesta etapa.
        page_title="Lotofácil Pro — Gerador & Conferidor",
        # page_icon recebe o valor que define o texto ou identificador `"🎱",` usado nesta etapa.
        page_icon="🎱",
        # layout recebe o valor que define o texto ou identificador `"wide",` usado nesta etapa.
        layout="wide",
        # initial_sidebar_state recebe o valor que define o texto ou identificador `"collapsed",` usado nesta etapa.
        initial_sidebar_state="collapsed",
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )
    # Aplica os estilos externos uma vez, apos configurar a pagina e antes de renderizar os modulos.
    st.markdown(MODERN_CSS, unsafe_allow_html=True)

    # Hero Header Sem Imagem de Logo
    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-badge">🎱 LOTOFÁCIL INTELIGENTE</div>
            <h1 class="hero-title">Gerador & Conferidor Pro</h1>
            <p class="hero-subtitle">Geração de combinações estratégicas, interseções de arquivos e conferência de concursos da Lotofácil.</p>
        </div>
        """,  # Fecha o fragmento HTML e o entrega ? chamada que o renderiza.
        # unsafe_allow_html recebe o valor que armazena em `unsafe_allow_html` o valor obtido de `True,`.
        unsafe_allow_html=True,
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )

    # Verifica se `"active_section" not in st.session_state`.
    if "active_section" not in st.session_state:
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        st.session_state["active_section"] = "Gerador de Combinações"

    # active_section recebe o valor que armazena em `active_section` o valor obtido de `st.radio(`.
    active_section = st.radio(
        # Fornece este texto como item da colecao ou argumento da chamada iniciada acima.
        "Navegação",
        # Continua a expressao composta iniciada acima com este operando.
        ["Gerador de Combina\u00e7\u00f5es", "Gerador por Grupos", "M\u00f3dulo A/B/C", "Imprimir Folha Loto", "Conferidor"],
        # horizontal recebe o valor que armazena em `horizontal` o valor obtido de `True,`.
        horizontal=True,
        # key recebe o valor que define o texto ou identificador `"active_section",` usado nesta etapa.
        key="active_section",
        # label_visibility recebe o valor que define o texto ou identificador `"collapsed",` usado nesta etapa.
        label_visibility="collapsed",
    # Fecha o agrupamento da chamada ou colecao iniciada acima.
    )

    # Chama `st.markdown` para renderiza texto Markdown ou HTML na interface.
    st.markdown("<br>", unsafe_allow_html=True)

    # Verifica se `active_section == "Gerador de Combinações"`.
    if active_section == "Gerador de Combinações":
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        render_generator()
    # Verifica se a secao de geracao por grupos esta selecionada.
    elif active_section == "Gerador por Grupos":
        # Renderiza a configuracao e os resultados do gerador por grupos.
        render_group_generator()
    # Verifica a proxima condicao: `active_section == "Módulo A/B/C"`.
    elif active_section == "Módulo A/B/C":
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        render_intersection_module()
    # Verifica a proxima condicao: `active_section == "Imprimir Folha Loto"`.
    elif active_section == "Imprimir Folha Loto":
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        render_print_module()
    # Inicia o caminho alternativo quando as condicoes anteriores nao foram atendidas.
    else:
        # Compoe a expressao ou os argumentos da operacao iniciada acima.
        render_checker()


# Verifica se `__name__ == "__main__"`.
if __name__ == "__main__":
    # Compoe a expressao ou os argumentos da operacao iniciada acima.
    main()
