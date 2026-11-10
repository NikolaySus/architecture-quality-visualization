"""Read-only explorer. Run with streamlit run research/language_resources/app.py."""

from html import escape
from datetime import datetime
from pathlib import Path
import sys
import textwrap
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from research.language_resources import pipeline, queries
from research.language_resources.storage import CATALOG, Workspace


def select_entity(entity_id, view):
    st.session_state["entity_id"] = entity_id
    st.session_state["view"] = view


@st.cache_data(show_spinner=False)
def available_kinds(database):
    return queries.kinds(Path(database))


def graph_html(graph, root=None):
    from pyvis.network import Network

    network = Network(height="650px", width="100%", directed=True, cdn_resources="in_line")
    for node in graph["nodes"]:
        color = "#d88700" if node["id"] == root else "#288270" if node["source"] is None else "#6d91c4"
        network.add_node(node["id"], label=textwrap.fill(node["label"][:80], width=28),
                         title=escape(f"{node['kind']} · {node['source'] or 'shared'} · {node['id']}"),
                         color=color, size=18 if node["id"] == root else 11)
    for edge in graph["edges"]:
        network.add_edge(edge["subject_id"], edge["object_id"], label=edge["predicate"].split(":", 1)[-1],
                         title=escape(f"{edge['predicate']} · {edge['rule']} · {edge['file']} · {edge['record']}"),
                         dashes=edge["rule"] != "source")
    network.set_options('''{
      "interaction":{"hover":true,"navigationButtons":true},
      "nodes":{"font":{"size":13}},
      "edges":{"font":{"size":10,"align":"middle"},"smooth":{"type":"continuous"}},
      "physics":{"barnesHut":{"gravitationalConstant":-10000,"centralGravity":0.08,
        "springLength":180,"springConstant":0.03,"avoidOverlap":0.7},
        "stabilization":{"iterations":250}}
    }''')
    # PyVis in_line still adds optional Bootstrap CDN tags in its stock template.
    document = BeautifulSoup(network.generate_html(), "html.parser")
    for resource in document.find_all(["script", "link"]):
        url = resource.get("src") or resource.get("href") or ""
        if url.startswith(("http://", "https://", "//")):
            resource.decompose()
    copy_status = document.new_tag("div", id="graph-copy-status", role="status")
    copy_status["style"] = ("position:fixed;top:8px;left:12px;right:12px;z-index:10;"
                            "font:13px sans-serif;color:#222;background:rgba(255,255,255,.95);"
                            "overflow-wrap:anywhere;")
    document.body.append(copy_status)
    copy_script = document.new_tag("script")
    copy_script.string = '''
      network.on("click", async function (event) {
        if (event.nodes.length !== 1) return;
        const objectId = String(event.nodes[0]);
        const status = document.getElementById("graph-copy-status");
        try {
          await navigator.clipboard.writeText(objectId);
          status.textContent = "Идентификатор скопирован · " + objectId;
        } catch (error) {
          status.textContent = "Браузер отклонил копирование. ID объекта · " + objectId;
        }
      });
    '''
    document.body.append(copy_script)
    return str(document)


def main():
    st.set_page_config(page_title="Языковые ресурсы", layout="wide")
    st.title("Общее представление русского языка")
    workspace = Workspace()
    state = pipeline.status(workspace)
    generation = state["generation"]
    view = st.sidebar.radio("Раздел", ["Источники", "Поиск", "Карточка объекта", "Граф"], key="view")
    if generation:
        created_at = datetime.fromisoformat(generation["created_at"]).astimezone(ZoneInfo("Europe/Moscow"))
        st.caption(f"Сборка {generation['id'][:12]} · {created_at:%d.%m.%Y %H:%M} МСК")
        columns = st.columns(3)
        columns[0].metric("Объекты", f"{generation['counts']['entity']:,}")
        columns[1].metric("Связи", f"{generation['counts']['fact_relation']:,}")
        columns[2].metric("Источники в сборке", len(generation["inputs"]["snapshots"]))
    if state["stale"]:
        st.info("Для актуального представления выполните python -m research.language_resources rebuild")
    if state["last_build"] and state["last_build"]["status"] == "error":
        st.error("Последняя сборка завершилась ошибкой. " + state["last_build"]["error"])
    if view == "Источники":
        summary = [{"Источник": row["title"], "Загружен": row["available"], "Полный": row["complete"],
                    "МБ": round(row["bytes"] / 1_000_000, 2), "Снимок": (row["snapshot"] or "")[:12],
                    "В сборке": row["snapshot"] is not None and row["snapshot"] == row["warehouse_snapshot"]}
                   for row in state["sources"]]
        st.dataframe(pd.DataFrame(summary), hide_index=True, width="stretch")
        for row in state["sources"]:
            with st.expander(row["title"]):
                st.json(row)
                st.link_button("Страница источника", CATALOG[row["source"]]["url"])
        if generation and generation.get("diagnostics"):
            with st.expander("Диагностика обработки"):
                st.json(generation["diagnostics"])
        return
    database = workspace.database(generation) if generation else None
    if database is None or not database.exists():
        st.info("Загрузите или импортируйте источники и выполните rebuild. Статус доступен в разделе «Источники».")
        return
    if view == "Поиск":
        text = st.text_input("Текст, лемма или идентификатор", key="search_text")
        filters = st.columns(3)
        source = filters[0].selectbox("Источник", [None, "shared", *CATALOG],
            format_func=lambda value: "Все" if value is None else "Общие объекты" if value == "shared" else CATALOG[value]["title"])
        kind = filters[1].selectbox("Тип объекта", [None, *available_kinds(str(database))],
                                    format_func=lambda value: value or "Все")
        page = filters[2].number_input("Страница", min_value=1, value=1, step=1)
        rows, more = queries.search(database, text, source, kind, page=int(page) - 1)
        st.caption(f"Записей на странице {len(rows)} · следующая страница {'есть' if more else 'отсутствует'}")
        selection = st.dataframe(pd.DataFrame(rows, columns=["label", "kind", "source", "local_id", "id"]),
            column_config={"label": st.column_config.TextColumn("Объект", width="large"),
                           "kind": st.column_config.TextColumn("Тип", width="small"),
                           "source": st.column_config.TextColumn("Источник", width="small"),
                           "local_id": st.column_config.TextColumn("Исходный ID", width="medium"),
                           "id": st.column_config.TextColumn("ID", width="small")},
            hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key="results")
        if rows:
            index = selection.selection.rows[0] if selection.selection.rows else 0
            if index < len(rows):
                chosen = rows[index]["id"]
                columns = st.columns(2)
                columns[0].button("Открыть карточку", on_click=select_entity, args=(chosen, "Карточка объекта"))
                columns[1].button("Открыть граф", on_click=select_entity, args=(chosen, "Граф"))
        return
    entity_id = st.text_input("Идентификатор объекта", key="entity_id")
    if not entity_id:
        st.info("Выберите объект в разделе «Поиск» или введите его полный идентификатор.")
        return
    card = queries.entity_card(database, entity_id)
    if not card:
        st.warning("Объект отсутствует в этой сборке.")
        return
    st.subheader(card["label"])
    st.caption(f"{card['kind']} · {card['namespace']} · {card['local_id']}")
    if view == "Карточка объекта":
        st.write("Атрибуты и исходная запись")
        st.json(card["attributes"])
        st.write("Происхождение")
        st.dataframe(pd.DataFrame(card["evidence"]).reindex(columns=["source", "file", "record", "rule", "entity_id"]),
            column_config={"source": st.column_config.TextColumn("Источник", width="small"),
                           "file": st.column_config.TextColumn("Файл", width="medium"),
                           "record": st.column_config.TextColumn("Запись", width="large")},
            hide_index=True, width="stretch")
        st.write("Входящие и исходящие связи")
        st.dataframe(pd.DataFrame(card["relations"]).reindex(columns=["subject_label", "predicate", "object_label",
            "source", "rule", "file", "record", "id", "subject_id", "object_id", "attributes"]),
            column_config={"subject_label": st.column_config.TextColumn("Субъект", width="medium"),
                           "predicate": st.column_config.TextColumn("Отношение", width="medium"),
                           "object_label": st.column_config.TextColumn("Объект", width="medium")},
            hide_index=True, width="stretch")
        if card["relation_origins"]:
            st.write("Основания преобразования отношений")
            st.dataframe(pd.DataFrame(card["relation_origins"]).reindex(columns=[
                "relation_id", "mapping_rule", "original_subject_label", "predicate", "original_object_label",
                "source", "file", "record", "rule", "id", "mapping_attributes", "attributes"]),
                hide_index=True, width="stretch")
        if card["truncated"]:
            st.info("Показаны первые 200 записей происхождения и связей.")
        st.button("Исследовать граф", on_click=select_entity, args=(entity_id, "Граф"))
    else:
        depth = st.slider("Глубина", min_value=1, max_value=3, value=1)
        limits = st.columns(2)
        node_limit = limits[0].number_input("Предел узлов", min_value=1, value=200, step=1, key="graph_node_limit")
        edge_limit = limits[1].number_input("Предел связей", min_value=1, value=5000, step=1, key="graph_edge_limit")
        graph = queries.neighborhood(database, entity_id, depth=depth, limit=node_limit, edge_limit=edge_limit)
        st.caption(f"Узлов {len(graph['nodes'])} · связей {len(graph['edges'])} · корень выделен оранжевым. "
                   "Нажмите на вершину, чтобы скопировать идентификатор объекта.")
        if graph["truncated"]:
            st.info(f"Окрестность усечена. Предел узлов равен {node_limit}, предел связей — {edge_limit}.")
        components.html(graph_html(graph, root=entity_id), height=680, scrolling=True)
        options = {node["id"]: node["label"] for node in graph["nodes"]}
        selected = st.selectbox("Перейти к объекту окрестности", list(options),
                                format_func=lambda value: options[value] + " · " + value[:12])
        st.button("Сделать корнем графа", on_click=select_entity, args=(selected, "Граф"))


if __name__ == "__main__":
    main()
