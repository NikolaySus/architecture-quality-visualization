# Анализ выбора бенчмарков ruMTEB и сборка отчёта

Здесь собраны анализ 23 задач MTEB(rus, v1.1), обоснование выбора четырёх
задач поиска/переранжирования и воспроизводимая сборка итогового DOCX.
Перенесена утверждённая версия от **15 сентября 2026 года, 16:19:44 МСК**,
ранее находившаяся в `bmstu/m3/Эр`. Все зависимости от этой директории устранены.

Итоговый отчёт содержит три альбомные страницы A4: сводку по 23 задачам,
подробную таблицу четырёх выбранных бенчмарков и пояснения к метрикам с
формулами и источниками. Текст, оформление и исторические значения сохранены.
Это не обновление обзора на дату переноса.

## Содержимое

| Путь | Назначение |
|---|---|
| `ANALYSIS.md` | Выводы, критерии отбора, исправления чисел и ограничения |
| `inputs/MTEB_rus_v1_1_23_benchmarks.xlsx` | Исходные три листа с обзором и источниками |
| `inputs/overview_template.docx` | Исходный шаблон утверждённой первой страницы |
| `data/selected_benchmarks.json` | Редактируемое содержание подробной таблицы четырёх задач |
| `data/provenance.json` | Происхождение, SHA-256 входов и эталонных частей OOXML |
| `evidence/` | Сохранённые статистики, результаты лидерборда и исходные файлы RuBQ |
| `scripts/analyze.py` | Проверка среза данных, отбора и численных утверждений |
| `scripts/build_report.py` | Сборка утверждённого трёхстраничного DOCX |
| `scripts/build_overview.py` | Отдельная сборка базовой сводки из XLSX |
| `scripts/validate_report.py` | Проверка анализа и совпадения DOCX с историческим оригиналом |
| `output/` | Генерируемые отчёты, результаты проверки и рендеры; игнорируется Git |

Шаблон первой страницы является входным материалом сборки, а не итоговым
отчётом. Он сохраняет утверждённую в сессии вёрстку и редакторские правки.
`build_overview.py` восстанавливает базовую сводку из XLSX; точная финальная
сборка использует шаблон и дополнительно исправляет число запросов RuBQ.

## Воспроизведение

Команды выполняются из корня репозитория. Зависимости этого переноса
отделены от окружения основного приложения. Нужен Python 3.12 или новее.

```powershell
uv run --no-project --with-requirements research/rumteb_benchmark_selection/requirements.txt python research/rumteb_benchmark_selection/scripts/analyze.py
uv run --no-project --with-requirements research/rumteb_benchmark_selection/requirements.txt python research/rumteb_benchmark_selection/scripts/build_report.py
uv run --no-project --with-requirements research/rumteb_benchmark_selection/requirements.txt python research/rumteb_benchmark_selection/scripts/validate_report.py
```

После установки зависимостей сами анализ и сборка работают без сети.
Без uv можно установить `requirements.txt` в отдельное Python-окружение
и выполнить те же скрипты через его интерпретатор.

Результаты:

- `output/ruMTEB_23_обоснованность.docx` — итоговый отчёт;
- `output/analysis.json` — выгрузка трёх листов и проверенные статистики;
- `output/validation.json` — результат проверки сборки;
- `output/overview.docx` — базовая сводка, только если отдельно запущен `build_overview.py`.

Для экспорта DOCX в PDF нужен LibreOffice и шрифт Times New Roman.
Текущая раскладка в три страницы проверена в Windows с этими компонентами.

```powershell
& 'C:/Program Files/LibreOffice/program/soffice.exe' --headless --convert-to pdf --outdir research/rumteb_benchmark_selection/output 'research/rumteb_benchmark_selection/output/ruMTEB_23_обоснованность.docx'
```

В среде Codex для визуальной проверки использовался `render_docx.py`
навыка Documents с `--emit_pdf` и выходным каталогом `output/render`.
Этот инструмент не является зависимостью сборки DOCX. После изменения
содержания или вёрстки нужно заново проверить все страницы.

## Происхождение данных

Исходные локальные сессии: `01a0810a-86d4-7af1-a265-f8dbbeb68280`
и её продолжение `01a0a52f-29f2-7d51-9819-85b39c347d9a`.

Код задач и описательная статистика привязаны к коммиту MTEB
[`46003a16451d7221b9df6c435311480a3b5d6ebd`](https://github.com/embeddings-benchmark/mteb/tree/46003a16451d7221b9df6c435311480a3b5d6ebd).
Полные URL ревизий данных для четырёх задач находятся в
`data/selected_benchmarks.json`. Статистики в `evidence/*.json` взяты из
`mteb/descriptive_stats/Retrieval/` и `Reranking/` этого коммита.

Снимки `*_scores.json` сохранены из API MTEB leaderboard
`https://mteb-leaderboard-backend.hf.space/v1/tasks/{task}/scores`;
`rus_benchmark_scores.json` — из `/v1/benchmarks/MTEB(rus,%20v1.1)/scores`.
Время HTTP-ответов исходная сессия отдельно не зафиксировала; дата проверки
результатов в её отчёте — 15.09.2026. При повторном запросе API числа могут измениться.

`RuBQ_2.0_{dev,test}.json` и спецификация сохранены из
[RuBQ 2.0](https://github.com/vladislavneon/RuBQ/tree/master/RuBQ_2.0).
`rubq_queries.jsonl` и `rubq_qrels.jsonl` — из ревизии
[`e19b6ffa60b3bc248e0b41f4cc37c26a55c2a67b`](https://huggingface.co/datasets/ai-forever/rubq-retrieval/tree/e19b6ffa60b3bc248e0b41f4cc37c26a55c2a67b).
Полный корпус текстов MIRACL и RuBQ сюда не переносился. Происхождение и
условия использования сторонних данных сохраняются за их исходными проектами.
Правило `.gitattributes` сохраняет байты снимков `evidence/` при checkout,
чтобы автоматическая замена LF/CRLF не нарушала проверку SHA-256.

Генерируемые DOCX/PDF, выгрузки анализа и рендеры в `output/` не коммитятся.
Глобальное правило репозитория `*.pdf` также сохранено. Проверка
`validate_report.py` сравнивает все части OOXML с историческим оригиналом,
поэтому намеренное редактирование отчёта потребует явно установить новый
эталон; несовпадение не следует обходить автоматическим обновлением хешей.
