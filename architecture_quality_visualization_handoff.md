# Handoff для Codex: визуализация методов предсказания качества архитектуры

Версия: 0.2, 29 сентября 2026. Проект: НИР3+Э.
Статус: рабочая спецификация с исследовательским корпусом и исходными данными; предназначена для последующего дополнения.
Основной новый материал: **§8 — реестр источников и методов; §8.4 — численные таблицы; §8.5 — маршруты извлечения недостающих данных.**
Язык интерфейса и пояснений: русский; названия статей и метрик сохранять в оригинале.

## 1. Задача и контекст

Создать локальный инструмент для изучения статей и подходов к предсказанию качества нейросетевой архитектуры до её полноценного обучения и оценки. Инструмент должен показывать релевантность работ исследовательской задаче, особенности методов, ограничения применимости и возможные общие закономерности.

Целевая постановка: обучающие данные и бенчмарк фиксированы; меняется архитектура. Требуется предсказать итоговое качество либо ранжирование архитектур. Особый интерес представляет применение к моделям эмбеддингов текстов и случай без доступа к данным (data-free).

Начать с объяснимых двумерных графиков. Это инструмент обзора литературы, а не запуск собственного NAS или обучение моделей. В первой реализации не требуются GPU, LLM API, платные сервисы, обучение кандидатов или публичное размещение.

## 2. Происхождение требований и границы восстановления контекста

Основа — чат «Предсказание качества архитектуры» от 29.09.2026 и текущая просьба пользователя подготовить handoff для локального Codex. Доступны фрагмент сообщения пользователя и выборочно восстановленные сведения из истории; полного дословного чата в этом файле нет. В v0.2 выполнен отдельный поиск первоисточников и проверены библиографические записи; глубина проверки и готовность чисел указаны для каждого источника в §8. Не утверждать, что восстановлен полный список именно из прежнего чата.

**Подтверждённые требования пользователя:**

- Начать с 2D-графиков, визуализировать релевантность и особенности подходов, искать закономерности.
- Использовать три визуальных класса статей, описанные в следующем разделе.
- Рассмотреть зависимость заявленной точности предсказания от ресурсов/времени пробного обучения или инференса.
- Уделить особое внимание области около нулевых затрат и удобному масштабу этой области.
- Полноценное обучение и бенчмарк служат интуитивным ориентиром больших затрат и эталонной оценки.
- Класс применения к моделям эмбеддингов текстов пока оставить пустым; более подробный поиск статей предполагается позднее.

**Поручение пользователя для v0.2:** собрать список релевантных методов из статей, необходимые для визуализаций данные и метаданные поиска первоисточников; выделить это в важный самостоятельный раздел и при необходимости уточнить визуализации.

**Предложения составителя v0.1–v0.2:** конкретная схема данных, графики B–F, интерфейс, стек, нормализация и критерии готовности. Это рабочие решения для прототипа, а не ранее согласованные во всех деталях требования.

## 3. Визуальная семантика

| Класс | Смысл | Отображение |
|---|---|---|
| `relevant` | Релевантный подход, без подтверждённого применения к NLP-трансформерам в рассматриваемой работе | Приглушённая полупрозрачная заливка, пунктирная граница круга |
| `nlp_transformer` | Подход действительно применён к NLP-трансформерам | Непрозрачная заливка умеренной насыщенности, сплошная граница |
| `text_embedding` | Подход действительно применён к моделям эмбеддингов текстов | Яркая акцентная заливка, сплошная граница |

В легенде всегда показывать все три класса, включая «Модели эмбеддингов текстов — 0 подтверждённых работ» при пустом третьем классе. Пустота означает состояние нашего корпуса, а не доказанное отсутствие таких исследований.

Классы вложены по смыслу. В обзоре статей выбирать наиболее специфичный подтверждённый класс статьи; сохранять отдельные признаки применений. Для методов и наблюдений применять уточнение §4. Потенциальную переносимость на текстовые эмбеддинги не считать фактическим применением. Если класс ещё не проверен, оставлять его неопределённым и показывать работу в очереди проверки, без принудительного назначения `relevant`.

Обычный размер маркеров одинаков. Цвет и контур не перегружать дополнительными значениями. Для семейств подходов использовать фильтры и отдельные панели. Пунктир реализовать буквально, при необходимости через SVG-слой; не заменять молча сплошным контуром. Легенду и экспорт проверять визуально.

## 4. Что именно является точкой

Основная единица исследовательского каталога — метод из статьи. В обзоре публикаций точка может представлять статью; численные результаты принадлежат конкретному эксперименту. Одна статья может содержать несколько методов, бенчмарков и бюджетов.

Хранить связанные сущности `paper`, `method`, `observation`: у метода есть `origin_paper_id`, а у наблюдения — `evaluation_paper_id`. Они могут различаться. Не дублировать метод, когда его проверяет новая статья. На количественном графике одна точка — одно наблюдение: метод, набор архитектур, протокол оценки и бюджет. По клику показывать статью и все связанные наблюдения. Не усреднять разные эксперименты ради одной точки статьи. В общем обзоре статей допустимо по одной точке на работу с явно выбранным наблюдением; по умолчанию предпочтительнее фильтр протокола.

Уточнение v0.2: в каталоге метода показывать наиболее специфичное подтверждённое применение со ссылкой на evaluation paper; на численном графике класс определяется исследуемыми архитектурами конкретного наблюдения. Сохранять исходный класс статьи в карточке. CV-эксперимент из статьи, где есть NLP, остаётся CV-наблюдением; RNN не получает класс NLP Transformer. Применение LM внутри предиктора также не означает оценку NLP-кандидатов. Фильтр домена работает по наблюдениям.

## 5. Графики первой версии

### A. Основной: надёжность предсказания против вычислительных затрат

- X: стоимость оценки одной архитектуры либо полный бюджет процедуры — отдельные режимы, никогда не смешанные.
- Y: качество предсказания итогового результата или ранжирования архитектур.
- Начальный вариант Y: Spearman rho, если найдены подтверждённые сопоставимые данные. Kendall tau, Pearson r, MAE/RMSE, top-k recall и regret доступны отдельными представлениями.
- Оси всегда подписаны конкретной метрикой и единицами. Не называть корреляцию «процентом точности» и не совмещать разные метрики на общей шкале.
- Затраты: секунды, GPU-часы, FLOPs или доля стоимости полного обучения и оценки. Выбирать одну величину на панель. Показатели памяти — отдельная ось в другом представлении, не часть произвольного общего балла ресурсов.
- Время на разных устройствах не является автоматически сопоставимым: разделять панели/группы по условиям, показывать аппаратуру и протокол.
- Масштаб X: linear и symlog с видимым параметром линейной области; дополнительно увеличение ближней к нулю области. При обычном log ноль показывать отдельно, без подмены малым положительным числом.
- Неизвестные затраты — `null`, не 0. Отсутствие обучения не означает отсутствие вычислительных затрат.
- Для неполного учёта времени (§8.4 G2) предусмотреть явно подписанный предварительный режим; по умолчанию строгий режим требует известного scope и аппаратуры. Неполный тайминг не отображать как полную стоимость.
- Парето-фронт строить только внутри явно определённой сопоставимой группы; учитывать направление метрики. По умолчанию выключать при несопоставимых данных. Это фронт наблюдаемых точечных оценок, не доказательство статистического превосходства.

Полное обучение и бенчмарк показывать отдельным референсным маркером или аннотацией, а не четвёртым классом статьи. X=1 допустим при нормализации на тот же baseline. Y=1 допустим только как условное идеальное совпадение рангов с самим эталоном; не представлять это как эмпирически достигнутую абсолютную точность. Полное обучение не гарантирует максимальный бюджет среди всех процедур и не устраняет шум оценки.

### B. Требования к данным против надёжности предсказания

Категориальная X: доступ к реальным входным данным не нужен / нужны входы без разметки / нужны размеченные данные. Y — выбранная метрика из A, с теми же ограничениями сопоставимости. Потребность в синтетических входах и в исторических результатах обученных архитектур показывать отдельными признаками.

Особенно важно разделять data-free на этапе применения и потребность в данных на этапе построения предиктора. Training-free, data-free и отсутствие предварительно обученного предиктора — разные свойства.

### C. Первоначальные затраты против стоимости нового кандидата

X: стоимость подготовки/обучения предиктора, включая формирование обучающих меток, если известна. Y: стоимость оценки одной новой архитектуры. Этот график помогает отличить дешёвое применение дорогого предиктора от дешёвого метода целиком.

Отдельный интерактивный расчёт, только при наличии совместимых данных:

`C_total(N) = C_setup + N * C_candidate`

Отмечать, какие части стоимости учтены, какие исключены и допускается ли такое линейное приближение. Для active learning учитывать добавление новых quality labels, повторное fitting и меняющийся budget; не применять линейную формулу автоматически. Не подставлять нули вместо неизвестных затрат. Не добавлять стоимость подготовки повторно, если она уже включена в исходный total.

### D. Обзор методов при отсутствии чисел

Категориальная 2D-карта: семейство метода × условия доступа к данным. Использовать лишь проверенные категории; смещение точек внутри ячейки служит читаемости и не имеет количественного смысла. Эта карта позволяет начать с неполной литературы без вымышленных координат «точности» и «дешевизны».

Предлагаемые семейства: архитектурные признаки и surrogate models; zero-cost proxies; экстраполяция learning curves/обучение с малым бюджетом; оценка через общие или предсказанные веса; scaling laws. Разрешить несколько тегов. Это предварительная таксономия, которую можно уточнять по корпусу.

### E. Бюджет получения информации против качества прогноза

Для обучаемых предикторов X — число архитектур с известным итоговым качеством, Y — ранговая корреляция. Для learning-curve методов отдельный режим X — наблюдённые epochs/steps или доля полного обучения кандидата. Эти два бюджета не смешивать на одной оси. Соединять только точки одного метода и неизменного протокола; показать опубликованную неопределённость с её типом, например SD.

Начать с §8.4 G5; G7 показывать в отдельной панели с отметкой неуточнённого target dataset. Число labels не является временем: отдельно показывать, были ли labels взяты из готового benchmark или оплачены в данном поиске, и что известно о цене их получения. Для scaling laws использовать отдельную панель «диапазон экстраполяции/калибровочный бюджет → ошибка», когда значения будут извлечены; не выдумывать корреляцию из loss fit.

### F. Чувствительность к входным данным и перенос

Небольшие панели с одинаковой метрикой: один метод на разных proxy-input datasets, target tasks или search spaces. Это три разных изменения условий, требующие отдельных переключателей. Внутри строго согласованного протокола допустимы соединённые пары; между независимыми статьями — только раздельные панели с source labels.

G1/G2/G4 показывают повод для проверки устойчивости, но различия их чисел нельзя приписать только смене входного датасета: могут отличаться реализации, aggregation и ground truth. Сначала импортировать controlled comparisons из §8.5. Для каждого результата показывать источник, вариант proxy, target и размер выборки архитектур.

## 6. Сопоставимость и доказательства

Каждый численный результат должен иметь источник: URL, версию статьи, страницу/таблицу/рисунок и способ извлечения. Различать `reported`, `digitized`, `derived`, `unknown`. Для производной величины сохранять формулу и исходные значения. Не восстанавливать число из слов «высокая корреляция».

Группу сопоставимости определять через search space, датасет/задачу, целевой training recipe и бюджет, определение ground truth, разбиение train/test предиктора, метрику и способ измерения затрат. Одинаковое название метрики недостаточно. Не назначать общий `comparison_group_id` автоматически по одному полю.

Отдельно учитывать оценку внутри известного пространства архитектур и перенос на новые пространства/задачи. Не считать предсказание perplexity или LM loss непосредственным доказательством предсказания retrieval/STS качества эмбеддингов.

Если есть интервалы неопределённости, число seed или размер выборки архитектур, показывать их. Если нет — явно «не указано». Не строить регрессионные зависимости по нескольким несопоставимым точкам разных статей.

## 7. Структура данных

Предлагается JSON/YAML как редактируемый источник и явная схема валидации. Код отображения отделить от корпуса. Минимальные поля:

| Сущность | Поля |
|---|---|
| `paper` | `id`, `title`, `authors`, `year`, `url`, `source_version`, `verification_status`, `visual_class`, `application_evidence`, `notes` |
| `method` | `id`, `origin_paper_id`, `evaluation_paper_ids`, `name`, `method_variant_id`, `family_tags`, `predicted_target`, `data_access_at_use`, `synthetic_inputs_required`, `uses_target_labels`, `requires_candidate_training`, `requires_pretrained_weights`, `requires_trained_predictor`, `historical_performance_labels_required`, `setup_data_requirements` |
| `observation` | `id`, `method_id`, `evaluation_paper_id`, `domain`, `dataset`, `search_space`, `training_recipe`, `ground_truth_protocol`, `predictor_split`, `num_architectures`, `num_seeds`, `comparison_group_id`, `metric`, `cost`, `evidence` |
| `metric` | `name`, `value`, `direction`, `aggregation`, `uncertainty`, `extraction_status` |
| `cost` | `quantity`, `unit`, `value`, `scope`, `hardware`, `batch_size`, `setup_included`, `label_generation_included`, `baseline_id`, `normalization_formula`, `extraction_status` |
| `evidence` | `url`, `locator`, `supporting_excerpt_or_note`, `verified_at` |

Для нескольких стоимостей или метрик использовать массивы, а не перезаписывать значения. Boolean-признаки допускают `null` как «не установлено». Для обязательных категорий предусмотреть `unknown`. Отсутствие доказательств не интерпретировать как отрицательный результат.

Расширение схемы, необходимое для нового корпуса, задано в §8.6; использовать обе таблицы совместно.

Для заметок о потенциальном применении в нашей задаче хранить отдельное поле `transfer_hypothesis`: это аналитическая гипотеза, а не заявленный авторами результат.

## 8. Основной исследовательский корпус: методы, источники и данные

### 8.1. Область охвата и степень готовности

Срез литературы: **29.09.2026**. Реестр содержит **50 источников, 72 записи методов/вариантов и 8 блоков извлечённых данных**. Это полный реестр **отобранного корпуса v0.2**, покрывающий основные механизмы предсказания: статические признаки, сигналы при инициализации, обучаемые surrogate models, малобюджетное обучение, экстраполяцию, общие/предсказанные веса и scaling laws. Это не заявление об исчерпывающем поиске всех публикаций мира. Работы найдены по исходным упоминаниям, связанным первоисточникам и поиску новых работ 2025–2026 годов; формального систематического обзора с проверкой всех цитирующих работ пока нет.

Критерий включения: метод даёт оценку/порядок качества кандидатов дешевле целевого обучения и оценки либо предоставляет необходимый набор данных/контрольный протокол. Чистые алгоритмы генерации архитектур без отдельного механизма оценки, предсказание одной лишь latency и общие обзоры не становятся точками качества предсказания.

Источники ниже проверены на уровне, указанном в реестре: **F** — просмотрены релевантные части полного текста; **A** — подтверждены название и постановка по первичному abstract/странице публикации; **M** — доступна первичная библиографическая запись/поисковая выдача, полный текст не получен. Даже F не означает независимое воспроизведение результата. Числа, уже извлечённые для импорта, выделены в §8.4; остальные численные поля остаются `null` с конкретной очередью извлечения (§8.5).

Приоритеты: **P0** — NLP и источники готовых сопоставимых наблюдений; **P1** — основные переносимые методы; **P2** — контекст и смежные постановки. Приоритет — редакционная оценка релевантности нашей задаче, не научный рейтинг.

### 8.2. Библиографический реестр

ID источника стабилен между версиями. Ссылка в названии — каноническая точка входа; arXiv ID / ACL ID / PMLR URL позволяют получить PDF и BibTeX. Для arXiv использовать версию из численного блока; когда чисел ещё нет, при извлечении зафиксировать выбранный `vN`. `et al.` здесь — отображение первого автора, а не полный авторский список: полное поле `authors` импортировать из BibTeX первоисточника. Не выводить полных авторов из догадок. Репозиторий не подменяет публикацию.

| ID | Статья и первоисточник | Авторы; год/площадка | Уровень; роль |
|---|---|---|---|
| P01 | [Zero-Cost Proxies for Lightweight NAS](https://arxiv.org/abs/2101.08134) | Mohamed S. Abdelfattah et al.; ICLR 2021 | A; базовые proxies и reduced-training comparison |
| P02 | [Neural Architecture Search without Training](https://proceedings.mlr.press/v139/mellor21a.html) | Joe Mellor, Jack Turner, Amos Storkey, Elliot J. Crowley; ICML 2021 | A; NASWOT |
| P03 | [Pruning neural networks without any data by iteratively conserving synaptic flow](https://arxiv.org/abs/2006.05467) | Hidenori Tanaka et al.; NeurIPS 2020 | A; исходный SynFlow, первоначально pruning |
| P04 | [SNIP: Single-shot Network Pruning based on Connection Sensitivity](https://arxiv.org/abs/1810.02340) | Namhoon Lee et al.; ICLR 2019 | A; исходный pruning score |
| P05 | [Picking Winning Tickets Before Training by Preserving Gradient Flow](https://arxiv.org/abs/2002.07376) | Chaoqi Wang, Guodong Zhang, Roger Grosse; ICLR 2020 | A; GraSP |
| P06 | [Neural Architecture Search on ImageNet in Four GPU Hours: A Theoretically Inspired Perspective](https://arxiv.org/abs/2102.11535) | Wuyang Chen, Xinyu Gong, Zhangyang Wang; ICLR 2021 | A; TE-NAS |
| P07 | [Zen-NAS: A Zero-Shot NAS for High-Performance Image Recognition](https://openaccess.thecvf.com/content/ICCV2021/html/Lin_Zen-NAS_A_Zero-Shot_NAS_for_High-Performance_Image_Recognition_ICCV_2021_paper.html) | Ming Lin et al.; ICCV 2021 | A; Zen-Score |
| P08 | [EZNAS: Evolving Zero Cost Proxies For Neural Architecture Scoring](https://arxiv.org/abs/2209.07413) | Yash Akhauri, J. Pablo Munoz, Nilesh Jain, Ravi Iyer; NeurIPS 2022 | A; поиск proxy-формулы |
| P09 | [FreeREA: Training-Free Evolution-based Architecture Search](https://arxiv.org/abs/2207.05135) | Niccolò Cavagnero et al.; WACV 2023; arXiv 2022, v2 2023 | A; LogSynFlow и комбинация proxies |
| P10 | [ZiCo: Zero-shot NAS via Inverse Coefficient of Variation on Gradients](https://arxiv.org/abs/2301.11300) | Guihong Li et al.; ICLR 2023 | A; межпримерная вариативность градиентов |
| P11 | [AZ-NAS: Assembling Zero-Cost Proxies for Network Architecture Search](https://openaccess.thecvf.com/content/CVPR2024/html/Lee_AZ-NAS_Assembling_Zero-Cost_Proxies_for_Network_Architecture_Search_CVPR_2024_paper.html) | Junghyup Lee, Bumsub Ham; CVPR 2024 | A; четыре сигнала и агрегация рангов |
| P12 | [Surprisingly Strong Performance Prediction with Neural Graph Features](https://proceedings.mlr.press/v235/kadlecova24a.html) | Gabriela Kadlecová et al.; ICML 2024 | F; GRAF; [полный текст v2](https://arxiv.org/html/2404.16551v2) |
| P13 | [Encodings for Prediction-based Neural Architecture Search](https://proceedings.mlr.press/v235/akhauri24a.html) | Yash Akhauri, Mohamed S. Abdelfattah; ICML 2024 | F; FLAN, unified encodings; [прочитанная v1](https://arxiv.org/html/2403.02484v1) |
| P14 | [Transferrable Surrogates in Expressive Neural Architecture Search Spaces](https://proceedings.mlr.press/v293/qin25a.html) | Shiwen Qin et al.; AutoML 2025 | F; RF/XGB/LM predictors; [прочитанная v1](https://arxiv.org/html/2504.12971v1) |
| P15 | [Neural Predictor for Neural Architecture Search](https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/6926_ECCV_2020_paper.php) | Wei Wen et al.; ECCV 2020; arXiv:1912.00848 | A; GCN accuracy regressor |
| P16 | [BRP-NAS: Prediction-based NAS using GCNs](https://arxiv.org/abs/2007.08668) | Łukasz Dudziak et al.; 2020 | A; binary relation predictor |
| P17 | [BANANAS: Bayesian Optimization with Neural Architectures for Neural Architecture Search](https://ojs.aaai.org/index.php/AAAI/article/view/17233) | Colin White, Willie Neiswanger, Yash Savani; AAAI 2021 | A; ensemble predictor; arXiv:1910.11858 |
| P18 | [CATE: Computation-aware Neural Architecture Encoding with Transformers](https://proceedings.mlr.press/v139/yan21c.html) | Shen Yan, Kaiqiang Song, Fei Liu, Mi Zhang; ICML 2021 | A; обучаемая архитектурная кодировка |
| P19 | [Does Unsupervised Architecture Representation Learning Help Neural Architecture Search?](https://arxiv.org/abs/2006.06936) | Shen Yan et al.; 2020 | A; arch2vec |
| P20 | [Accelerating Neural Architecture Search using Performance Prediction](https://arxiv.org/abs/1705.10823) | Bowen Baker, Otkrist Gupta, Ramesh Raskar, Nikhil Naik; arXiv 2017 | A; regression по частичному обучению |
| P21 | [Learning Curve Prediction with Bayesian Neural Networks](https://openreview.net/pdf?id=S11KBYclx) | Aaron Klein, Stefan Falkner, Jost Tobias Springenberg, Frank Hutter; ICLR 2017 | F; LC-Net |
| P22 | [Speeding Up Automatic Hyperparameter Optimization of Deep Neural Networks by Extrapolation of Learning Curves](https://www.ijcai.org/Abstract/15/487) | Tobias Domhan, Jost Tobias Springenberg, Frank Hutter; IJCAI 2015 | F; probabilistic curve extrapolation |
| P23 | [Speedy Performance Estimation for Neural Architecture Search](https://arxiv.org/abs/2006.04492) | Binxin Ru et al.; NeurIPS 2021; arXiv 2020 | A; SoTL / training-speed signal |
| P24 | [How Powerful are Performance Predictors in Neural Architecture Search?](https://papers.nips.cc/paper/2021/hash/ef575e8837d065a1683c022d2077d342-Abstract.html) | Colin White, Arber Zela, Binxin Ru, Yang Liu, Frank Hutter; NeurIPS 2021 | A; общий evaluation framework, hybrid predictors; arXiv:2104.01177 |
| P25 | [NAS-Bench-x11 and the Power of Learning Curves](https://arxiv.org/abs/2111.03602) | Shen Yan, Colin White, Yash Savani, Frank Hutter; NeurIPS 2021 | A; curve surrogates и экстраполяция |
| P26 | [LiteTransformerSearch: Training-free Neural Architecture Search for Efficient Language Models](https://arxiv.org/abs/2203.02094) | Mojan Javaheripi et al.; NeurIPS 2022 | A; decoder parameter count, GPT-2/Transformer-XL |
| P27 | [Training-free Neural Architecture Search for RNNs and Transformers](https://aclanthology.org/2023.acl-long.142/) | Aaron Serianni, Jugal Kalita; ACL 2023 | F; hidden covariance, attention metrics, NAS-BERT; DOI 10.18653/v1/2023.acl-long.142 |
| P28 | [LPZero: Language Model Zero-cost Proxy Search from Zero](https://aclanthology.org/2024.findings-emnlp.502/) | Peijie Dong et al.; Findings EMNLP 2024 | F; [официальный PDF](https://aclanthology.org/2024.findings-emnlp.502.pdf); DOI 10.18653/v1/2024.findings-emnlp.502 |
| P29 | [ZeroLM: Data-Free Transformer Architecture Search for Language Models](https://arxiv.org/abs/2503.18646v1) | Zhen-Song Chen, Hong-Wei Ding, Xian-Jia Wang, Witold Pedrycz; preprint 2025 | F; [таблицы HTML v1](https://arxiv.org/html/2503.18646v1) |
| P30 | [Training-Free Transformer Architecture Search](https://openaccess.thecvf.com/content/CVPR2022/html/Zhou_Training-Free_Transformer_Architecture_Search_CVPR_2022_paper.html) | Qinqin Zhou et al.; CVPR 2022 | A; TF-TAS / DSS; arXiv:2203.12217 |
| P31 | [Training-Free Transformer Architecture Search With Zero-Cost Proxy Guided Evolution](https://doi.org/10.1109/TPAMI.2024.3378781) | Qinqin Zhou et al.; TPAMI 2024, 46(10):6525–6541 | A; T-Razor, включая BERT; [сообщение авторского университета](https://xaxq.xmu.edu.cn/en/info/1291/2704.htm) |
| P32 | [Zero-Shot Neural Network Evaluation with Sample-Wise Activation Patterns](https://arxiv.org/abs/2605.07378) | Yameng Peng et al.; 2026, заявлено принятие в TPAMI | F; [v1](https://arxiv.org/html/2605.07378v1); расширяет arXiv:2403.04161 |
| P33 | [ParZC: Parametric Zero-Cost Proxies for Efficient NAS](https://ojs.aaai.org/index.php/AAAI/article/view/33793) | Peijie Dong et al.; AAAI 2025 | A; MABN/DiffKendall; arXiv:2402.02105 (авторский состав версии отличается — не смешивать) |
| P34 | [ONNX-Net: Towards Universal Representations and Instant Performance Prediction for Neural Architectures](https://arxiv.org/abs/2510.04938) | Shiwen Qin et al.; preprint 2025 | A; ONNX-to-text surrogate и ONNX-Bench |
| P35 | [Towards Code-Oriented LM Embeddings for Surrogate-Assisted Neural Architecture Search](https://arxiv.org/html/2605.15649v1) | Pranav Somu, Advay Balakrishnan, Stepan Kravtsov, Aaron McDaniel, Jason Zutty; 2026 | F; COLE; расширение GECCO 2026, DOI 10.1145/3795101.3805435 |
| P36 | [InTrain: Intrinsic Trainability for Zero-Cost Neural Architecture Search](https://openaccess.thecvf.com/content/CVPR2026/html/Zhou_InTrain_Intrinsic_Trainability_for_Zero-Cost_Neural_Architecture_Search_CVPR_2026_paper.html) | Qinqin Zhou et al.; CVPR 2026 | M; новый proxy, детали требуют PDF |
| P37 | [ZAPS: Zero-Cost Active Proxy Search for Neural Architecture Search](https://arxiv.org/abs/2609.14184) | Hassan Touayouch, Rabie Najem, Mohammed Benjelloun; preprint 12.09.2026 | M; proxy selection + active learner, не нулевая стоимость всего поиска |
| P38 | [CoRA-NAS: Coarse Ranking and Anchor-Residual Refinement for Neural Architecture Search](https://arxiv.org/abs/2609.11884) | Yifan Yang et al.; preprint 10.09.2026 | A; статический rank prior + малобюджетная коррекция |
| P39 | [Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361) | Jared Kaplan et al.; 2020 | A; scaling по размеру/данным/compute |
| P40 | [Training Compute-Optimal Large Language Models](https://arxiv.org/abs/2203.15556) | Jordan Hoffmann et al.; 2022 | A; Chinchilla, compute-optimal fitting |
| P41 | [Scaling Laws vs Model Architectures: How does Inductive Bias Influence Scaling?](https://aclanthology.org/2023.findings-emnlp.825/) | Yi Tay et al.; Findings EMNLP 2023 | A; architecture-dependent scaling; arXiv:2207.10551 |
| P42 | [Scaling Laws Across Model Architectures: A Comparative Analysis of Dense and MoE Models in Large Language Models](https://aclanthology.org/2024.emnlp-main.319/) | Siqi Wang et al.; EMNLP 2024 | A; Dense/MoE; arXiv:2410.05661 |
| P43 | [HAT: Hardware-Aware Transformers for Efficient Natural Language Processing](https://aclanthology.org/2020.acl-main.686/) | Hanrui Wang et al.; ACL 2020 | A; оценка через SuperTransformer |
| P44 | [AutoTinyBERT: Automatic Hyper-parameter Optimization for Efficient Pre-trained Language Models](https://aclanthology.org/2021.acl-long.400/) | Yichun Yin et al.; ACL-IJCNLP 2021 | A; one-shot оценка BERT-кандидатов |
| P45 | [Parameter Prediction for Unseen Deep Architectures](https://arxiv.org/abs/2110.13100) | Boris Knyazev, Michal Drozdzal, Graham W. Taylor, Adriana Romero-Soriano; NeurIPS 2021 | A; GHN-2, предсказание весов — смежная постановка |
| P46 | [NAS-Bench-Suite-Zero: Accelerating Research on Zero Cost Proxies](https://arxiv.org/abs/2210.03230) | Arjun Krishnakumar et al.; NeurIPS Datasets and Benchmarks 2022 | F; 13 proxies / 28 задач; [Table 1, v1](https://arxiv.org/html/2210.03230v1) |
| P47 | [An Evaluation of Zero-Cost Proxies — from Neural Architecture Performance Prediction to Model Robustness](https://doi.org/10.1007/s11263-024-02265-7) | Jovita Lukasik, Michael Moeller, Margret Keuper; IJCV, online 2024 | F; clean/robustness prediction; ранняя работа GCPR 2023, arXiv:2307.09365 |
| P48 | [LogME: Practical Assessment of Pre-trained Models for Transfer Learning](https://proceedings.mlr.press/v139/you21b.html) | Kaichao You, Yong Liu, Jianmin Wang, Mingsheng Long; ICML 2021 | A; контрольная смежная задача: выбор готовых моделей |
| P49 | [Dextr: Zero-Shot Neural Architecture Search with Singular Value Decomposition and Extrinsic Curvature](https://arxiv.org/abs/2508.12977) | Rohan Asthana, Joschua Conrad, Maurits Ortmanns, Vasileios Belagiannis; 2025, заявлено принятие в TMLR | A; label-free proxy, CNN/AutoFormer |
| P50 | [Zero-Shot Neural Architecture Search with Weighted Response Correlation](https://arxiv.org/abs/2507.08841) | Kun Jing et al.; preprint 2025, v2 | A; WRCor и voting variants |

Из неясных упоминаний v0.1 идентифицированы Qin, Wang, GRAF и работа Lukasik. Нельзя установить, какая из двух работ с участием Lukasik имелась в виду ранее, поэтому сохранены обе (P12/P47). Оборванное «Liu» не является идентифицированной статьёй и не было произвольно привязано к однофамильцу.

### 8.3. Реестр методов и необходимые входы

В этом реестре **метод — механизм оценки**, а не весь алгоритм NAS. Кодировка без регрессионной головы не считается готовым предиктором. Один источник может дать несколько методов, один метод — результаты из нескольких источников.

Обозначения входов: **G** — описание архитектуры; **W0** — случайно инициализированные веса; **Wp** — обученные/наследованные веса; **X** — реальные примеры; **Y** — метки либо явно описанная self-supervised цель; **H** — исторические пары «архитектура–качество»; **LC** — частичная кривая обучения. Для X без Y использовать `unlabeled`; language-model loss имеет цель из самого текста и не равен «forward без цели».

Класс **R** = `relevant`, **N** = `nlp_transformer`, **?** = применение ещё не установлено. Для N после точки с запятой указан источник фактического NLP-применения, если он отличается от оригинального. Это максимальная подтверждённая применимость метода в корпусе; стиль конкретного наблюдения определяется его экспериментом (§3–4). `text_embedding` пока не подтверждён ни для одного метода. Наличие STS-B в GLUE или получение embeddings архитектур не является доказательством оценки bi-encoder моделей текстовых эмбеддингов.

| Метод ID | Механизм; источники | Входы и первоначальные затраты | Класс; приоритет |
|---|---|---|---|
| M01 | Total parameter count; P01/P26/P28 | G; без обучения предиктора | N; P0 |
| M02 | Decoder-only parameter count (LTS); P26 | G; исключение embedding-параметров проверить по определению статьи | N; P0 |
| M03 | FLOPs как baseline качества; P46/P32 | G + форма входа; не путать значение FLOPs модели со стоимостью вычисления proxy | N; P0 |
| M04 | SynFlow; P03, NAS-адаптация P01 | W0 + искусственный вход, backward; исходный метод data-free, NLP-адаптации проверять отдельно | N; P28; P0 |
| M05 | SNIP score; P04/P01 | W0 + X + цель, gradient sensitivity | N; P28; P0 |
| M06 | GraSP score; P05/P01 | W0 + X + цель, градиентные/второпорядковые операции | N; P28; P0 |
| M07 | GradNorm; P01 | W0 + X + цель, gradient norm | N; P28; P0 |
| M08 | Fisher proxy; P01 | W0 + X + цель; вариант Fisher и агрегацию хранить явно | N; P28; P0 |
| M09 | Jacobian covariance (`jacov`); P01/P46 | W0 + X; input Jacobian; не объединять с cosine без проверки реализации | R; P1 |
| M10 | Jacobian cosine / Jacobian score; P27/P28 | W0 + X; отдельная NLP-реализация | N; P0 |
| M11 | NASWOT / activation-distance family; P02 | W0 + X, forward; ReLU/GELU-адаптации являются вариантами | N; P27/P28; P0 |
| M12 | LogSynFlow; P09 | W0 + искусственный вход в исходной реализации; стабилизация gradient score | N; P28; P0 |
| M13 | TE-NAS: NTK condition + linear regions; P06 | W0 + входные пробы; вычисление Jacobian/NTK; точный тип проб проверить | R; P1 |
| M14 | Zen-Score; P07 | W0 + случайные синтетические входы, несколько forward | R; P1 |
| M15 | EZNAS discovered proxy; P08 | при применении W0 и сигналы выбранной формулы; discovery использует H и поиск | N; P28; P0 |
| M16 | FreeREA aggregate score; P09 | несколько proxies; считать стоимость всей комбинации | R; P1 |
| M17 | ZiCo; P10 | W0 + X + цель, статистика градиентов по примерам | R; P1 |
| M18 | AZ-NAS aggregate; P11 | W0 + пробы, совместный forward/backward, агрегация четырёх сигналов | R; P1 |
| M19 | DSS-indicator / TF-TAS; P30 | W0 + входные пробы, MSA diversity + MLP saliency | N; P29/P32; P0 |
| M20 | Synaptic diversity component; P30 | W0 + сигналы attention; отдельный компонент DSS | N; P28; P0 |
| M21 | Synaptic saliency component; P30/P28 | W0 + сигналы FFN; не считать синонимом whole-network SynFlow | N; P0 |
| M22 | Attention confidence; P27 | W0 + X без downstream-разметки, attention statistics | N; P0 |
| M23 | Head/attention importance; P27/P28 | W0 + X; точный алгоритм и наличие backward определяются реализацией | N; P0 |
| M24 | Attention softmax confidence; P27/P32 | W0 + X, forward | N; P0 |
| M25 | LPZero discovered formula; P28 | W0 + X + статистики формулы; proxy discovery требует H | N; P0 |
| M26 | ZeroLM, benchmark-calibrated alpha; P29 | W0 или Wp; настройка alpha использует H | N; P0 |
| M27 | ZeroLM, heuristic alpha; P29 | W0 или Wp + выборка архитектур без quality labels; отдельный вариант | N; P0 |
| M28 | T-Razor evaluation proxy; P31 | модульные сигналы Transformer; точный ввод/формулу уточнить по полному тексту | N; P0 |
| M29 | SWAP-Score; P32 | W0 + X без меток, sample-wise activation patterns | N; P0 |
| M30 | Regularised SWAP-Score; P32 | M29 + параметрический prior размера; калибровка по выборке G | R; P1; NLP-вариант отдельно проверить |
| M31 | ParZC / MABN + DiffKendall; P33 | node-wise proxy features + H для обучения предиктора | R; P1 |
| M32 | Dextr; P49 | W0 + один неразмеченный пример; feature SVD и curvature | R; P1 |
| M33 | WRCor; P50 | W0 + X; корреляции ответов | R; P1 |
| M34 | WRCor voting; P50 | ансамбль proxies; точный состав и вычисления уточнить | R; P1 |
| M35 | InTrain; P36 | пока `unknown`, не достраивать механизм из названия | ?; P1 |
| M36 | GRAF + RF; P12 | G при применении; H для RF | R; P0 |
| M37 | ZCP + RF; P12 | proxy-вектор; H для RF | R; P0 |
| M38 | GRAF + ZCP + RF; P12 | G + proxy-вектор; H для RF | R; P0 |
| M39 | GRAF + ZCP + XGB/XGB+; P12/P14 | те же входы; сохранить regressor_variant | R; P0 |
| M40 | FLAN; P13 | G; structural/learned/score encodings по варианту; H и возможный pretraining | R; P0 |
| M41 | GCN Neural Predictor; P15 | G; H для регрессора | R; P1 |
| M42 | BRP pairwise GCN; P16 | G; H преобразуются в пары/отношения | R; P1 |
| M43 | BANANAS ensemble predictor; P17 | structural/path encoding G; H для ансамбля | R; P1 |
| M44 | CATE + prediction head; P18/P13 | pretraining на G; H для supervised head | R; P1 |
| M45 | arch2vec + prediction head; P19/P13 | unsupervised G pretraining; H для head | R; P1 |
| M46 | Fine-tuned LM surrogate (Qin); P14 | string(G); H и pretrained LM; отдельные backbone/augmentation варианты | R; P0 |
| M47 | Few-shot prompted LM surrogate (Qin); P14 | string(G) + примеры H в prompt, готовый LM | R; P1 |
| M48 | ONNX-Net surrogate; P34 | ONNX/text(G); обученный LM surrogate и H | R; P1 |
| M49 | COLE + PCA + MLP ranker; P35 | code(G), frozen LM; H для PCA/head по протоколу | R; P0 |
| M50 | ZAPS proxy/topology active ensemble; P37 | G + proxies + растущие H; paid evaluations входят в бюджет | R; P1 |
| M51 | CoRA-Rank; P38 | признаки при инициализации, log-rank consensus; детали проб уточнить | R; P1 |
| M52 | CoRA-Refine; P38 | M51 + LC якорей + ExtraTrees residual model | R; P1 |
| M53 | Baker regression / SVR; P20 | G + hyperparameters + LC; исторические завершённые кривые | R; P1; NLP здесь не автоматически Transformer |
| M54 | LC-Net; P21 | конфигурация/бюджет + LC training corpus; BNN fitting | R; P1 |
| M55 | Domhan curve extrapolation; P22 | LC кандидата; вероятностный fit кривой | R; P1 |
| M56 | SoTL / training-speed estimator; P23 | реальные training steps и их losses; без отдельного surrogate fitting | R; P1 |
| M57 | Learning-curve extrapolation framework; P25 | G/LC по выбранной реализации; различать реальную и surrogate ground truth | R; P1 |
| M58 | Hybrid/omni predictor; P24 | комбинация G, zero-cost features, LC; H; конфигурацию сверить в статье | R; P1 |
| M59 | Scaling-law predictor Kaplan; P39 | N,D,C и исторические обучающие прогоны для fit | N; P2 |
| M60 | Chinchilla fitted loss model; P40 | N,D,C + калибровочные прогоны | N; P2 |
| M61 | Architecture-conditioned scaling; P41 | семейство архитектуры + scale + результаты малых/средних запусков | N; P0 |
| M62 | Dense/MoE scaling fits; P42 | активные/полные параметры, данные/compute, калибровочные прогоны | N; P1 |
| M63 | HAT inherited-weight evaluation; P43 | обученный SuperTransformer + validation data; дорогой setup | N; P1 |
| M64 | AutoTinyBERT one-shot evaluation; P44 | обученная общая модель/дистилляция + task evaluation | N; P1 |
| M65 | GHN-2 predicted-weight evaluation; P45 | G → predicted W; обученная hypernetwork и данные для проверки W | R; P2; indirect evaluator |
| M66 | LogME transferability score; P48 | Wp + размеченные target features; pretraining уже выполнен | R; P2; не architecture-only |
| M67 | RF clean/robustness predictor; P47 | ZCP/GRAF + H для конкретной clean/attack цели | R; P1 |
| M68 | Hidden covariance; P27 | W0 + X; covariance скрытых состояний RNN; NAS-Bench-NLP | R; P1; NLP здесь не Transformer |
| M69 | One-hot architecture + RF; P12 | G; H для RF, контрольный encoding baseline | R; P1 |
| M70 | L2-norm baseline; P01/P46 | W0; без реальных примеров; агрегацию сверить с кодом | R; P1 |
| M71 | Plain baseline; P01/P46 | W0 + X; gradient-based baseline, формулу сверить с реализацией | R; P1 |
| M72 | EPE-NAS; evaluation P46 Table 1 | W0 + X, Jacobian; требования к Y и origin paper уточнить по ссылке [20] P46 | R; P1 |

Группы M13, M18, M39, M40, M46–M47 и M58 содержат варианты. Не превращать результаты разных вариантов в одну агрегированную точку; `method_variant_id` обязателен. Компоненты AZ-NAS можно дополнительно импортировать как expressivity/progressivity/trainability/complexity, сохранив связь `component_of=M18`.

Baseline-набор при вычислении новых сравнений: M01, M03; для decoder LM также M02; ранняя validation metric с явно заданным бюджетом; случайное ранжирование с несколькими seed. Значение корреляции случайного baseline измерять/моделировать, не изображать автоматически одной эмпирической точкой 0. Полное обучение — отдельный референс, как описано в §5A.

### 8.4. Извлечённые численные данные для немедленного импорта

Общие правила: числа ниже — **заявленные авторами**, не наши измерения. `null` — отсутствует в текущем извлечении; это не утверждение, что величины нет во всей статье. Каждая строка + каждый бюджет задают отдельное observation; rho и tau — две метрики того же observation. Сохранять исходное число без «улучшения» округления. В `evidence` записывать P-ID, URL конкретной версии и locator блока.

#### G1. LPZero: FlexiBERT, OpenWebText, 500 архитектур

Источник P28, официальный PDF, Table 2, печатная с. 8596 (PDF page 5); таблица визуально сверена. Target: средний downstream GLUE; `target_direction=max`. Batch input — OpenWebText. Cost каждой строки `null`. `comparison_group_id=lpzero2024_flexibert_t2`.

| method_id | Вариант | Kendall tau | Spearman rho |
|---|---|---:|---:|
| M20 | Synaptic Diversity | 0.021 | 0.175 |
| M23 | Head Importance | 0.050 | 0.171 |
| M11 | Activation Distance | 0.081 | 0.123 |
| M10 | Jacobian Cosine | 0.116 | 0.149 |
| M05 | SNIP | 0.119 | 0.173 |
| M06 | GraSP | 0.122 | 0.179 |
| M07 | GradNorm | 0.133 | 0.197 |
| M08 | Fisher | 0.139 | 0.209 |
| M21 | Synaptic Saliency | 0.157 | 0.266 |
| M04 | Synflow | 0.322 | 0.471 |
| M12 | LogSynflow | 0.334 | 0.491 |
| M01 | No.Params. | 0.454 | 0.590 |
| M22 | Attention Confidence | 0.475 | 0.666 |
| M15 | EZNAS | 0.483 | 0.698 |
| M25 | LPZero | 0.511 | 0.748 |

P28 §4.1, с.8597: proxy discovery — 10 GPU-hours; 50 архитектур для оценки формул. Это `scope=proxy_discovery`, не query time и не стоимость получения benchmark labels. Указаны A6000/H800; конкретное устройство данного тайминга не разделено.

#### G2. ZeroLM: FlexiBERT, WikiText-103, 500 архитектур

Источник P29 v1, Table I и §IV-A. Batch=128, length=256. Target=GLUE. Извлечена выборка строк с разными механизмами; в первоисточнике есть остальные baselines. `comparison_group_id=zerolm2025_flexibert_wikitext_t1`.

| method_id | Вариант | tau | rho | Reported time, s |
|---|---|---:|---:|---:|
| M01 | #params | 0.454 | 0.652 | null |
| M04 | Synflow | -0.320 | -0.470 | 6.805 |
| M25 | LPZero | 0.126 | 0.187 | 2.001 |
| M19 | DSS | 0.192 | 0.293 | 0.686 |
| M15 | EZNAS | 0.479 | 0.696 | 6.680 |
| M22 | Attention Confidence | 0.473 | 0.714 | 0.258 |
| M11 | Activation Distance | 0.518 | 0.739 | 0.198 |
| M26/M27 | Ours: variant unresolved | 0.532 | 0.765 | 0.883 |

Time описан как average; аппаратура и полный охват операций здесь не установлены. Хранить `cost_scope=reported_average_unresolved`, `hardware=null`, `cost_comparability=provisional`. Разрешён предварительный график с этой подписью; строгий Парето-фронт до проверки выключен. Последнюю строку не дублировать в обоих вариантах ZeroLM: временный `method_variant_id=zerolm_reported_unspecified`.

#### G3. LPZero: GPT-2, WikiText-103, 200 архитектур

P28, Table 3, с.8597 (PDF page 6); визуально сверено. Selected rows. `comparison_group_id=lpzero2024_gpt2_t3`. Положительные корреляции приведены в ориентации статьи; точное преобразование perplexity уточнить перед совместной шкалой.

| method_id | tau | rho |
|---|---:|---:|
| M01 | 0.582 | 0.737 |
| M22 | 0.676 | 0.850 |
| M12 | 0.836 | 0.962 |
| M02 | 0.847 | 0.967 |
| M25 | 0.886 | 0.980 |

#### G4. SWAP: FlexiBERT / GLUE, 500 архитектур

P32 v1, Table I, §IV-B. `comparison_group_id=swap2026_flexibert_t1`; вход OpenWebText, random-initialized кандидаты. `cost=null`, `tau=null`. Weighted GLUE aggregation этой статьи сохранять отдельно.

| method_id | Вариант | rho |
|---|---|---:|
| M20 | Synaptic Diversity | 0.169 |
| M21 | Synaptic Saliency | 0.177 |
| M11 | Activation Distance | 0.031 |
| M10 | Jacobian Score | 0.016 |
| M22 | Attention Confidence | 0.666 |
| M23 | Attention Importance | 0.162 |
| M24 | Attention Softmax Confidence | 0.055 |
| M19 | DSS-Indicator | -0.071 |
| M01 | #Params | 0.653 |
| M03 | #FLOPs | 0.652 |
| M29 | SWAP-Score | 0.711 |

#### G5. GRAF: NB101 / CIFAR-10, зависимость от числа меток

P12, arXiv:2404.16551v2, Appendix F, Table 6. Mean ± **standard deviation**, 50 runs, target validation accuracy. `comparison_group_id=graf2024_nb101_c10_t6`; каждое N — отдельный observation. RF default; OH=one-hot encoding, M69.

| Метод | N=32: tau ± SD | N=128: tau ± SD | N=1024: tau ± SD |
|---|---:|---:|---:|
| M69: RF + OH | 0.24 ± 0.09 | 0.40 ± 0.06 | 0.60 ± 0.02 |
| M36: RF + GRAF | 0.54 ± 0.08 | 0.63 ± 0.04 | 0.71 ± 0.01 |
| M37: RF + ZCP | 0.48 ± 0.05 | 0.56 ± 0.02 | 0.63 ± 0.01 |
| M38: RF + ZCP + GRAF | 0.56 ± 0.07 | 0.66 ± 0.04 | 0.73 ± 0.01 |

Тот же источник, Appendix E, Table 4: извлечение GRAF для **всей выборки** NB101 — 6.1 s / 10 000 architectures на Ryzen 7 3800X; среднее 10 повторов. Производная амортизированная величина: 0.00061 s/architecture, `scope=feature_extraction_amortized`, `status=derived`; это не полный query-time RF и не latency одиночного вызова.

#### G6. Qin: einspace / CIFAR-10, различные surrogate backbones

P14, arXiv:2504.12971v1, Table 1 и Data paragraph. Около 9k architecture–accuracy pairs, восемь NAS runs: 6 train / 1 validation / 1 test. `comparison_group_id=qin2025_cifar10_t1`; costs `null`.

| method_id | Вариант | rho | tau |
|---|---|---:|---:|
| M38 | RF, ZCP + GRAF | 0.663 | 0.514 |
| M39 | XGBRegressor, ZCP + GRAF | 0.600 | 0.449 |
| M46 | RoBERTa-base | 0.723 | 0.575 |
| M46 | ModernBERT-base | 0.746 | 0.597 |
| M46 | ModernBERT-large | 0.745 | 0.612 |
| M46 | ModernBERT-large + augmentation | 0.769 | 0.628 |

Это CV-цель; использование RoBERTa/ModernBERT внутри предиктора не даёт класс N. Указанная group не объединяется с G5 и G7.

#### G7. COLE: label-efficiency, NAS-Bench-201

P35 v1, §4.1.1–4.1.2, Table 1. Base: frozen CodeLlama-Python-7B, PCA128, MLP с pairwise loss. 10 folds × 10 seeds; размер выборки архитектур 15 625. `comparison_group_id=cole2026_nb201_base_t1`; точный target dataset Table 1 дополнительно уточнить — не переносить CIFAR-100 из отдельного NAS-эксперимента. Пока `dataset=unresolved`, разрешена только панель с исходной подписью.

| method_id | N labels | mean tau |
|---|---:|---:|
| M49 | 14 | 0.463 |
| M49 | 55 | 0.547 |
| M49 | 220 | 0.620 |
| M49 | 879 | 0.703 |
| M49 | 3516 | 0.797 |

Указана возможность запуска на одной H100; это не измерение runtime. `cost=null`. Таблицы 1/3 не дублировать как независимые эксперименты, если повторяется Base.

#### G8. Контекстные результаты с ограниченной готовностью

| method_id | Источник/locator | Извлечённая величина | Как использовать |
|---|---|---|---|
| M40 | P13 v1, Appendix A.5 | median predictor training ≈7.5 min; transfer maximum ≈1 min | Карточка setup; median и maximum разного scope, без выдуманной пары с корреляцией |
| M50 | P37, abstract | NB201, B=200 evaluations: top-100 recall 0.523 на CIFAR-10, 0.658 на CIFAR-100 | Отдельная search-recovery панель; full protocol pending |
| M52 | P38, abstract | mean rho: NB201 0.946; NB101 0.715; TNB101 0.786; NATS-SSS 0.894 | Четыре summary observations; не смешивать с single-task rho |
| M52 | P38, abstract | refinement ≈1% стоимости полного обучения candidate set | Только карточка до установления denominator, числа anchors и бюджета |

### 8.5. Что извлечь дополнительно: конкретные маршруты

Ниже не обещание, что все поля опубликованы. Агент проверяет указанные места, фиксирует `not_reported`, если просмотрел полный текст и supplementary, либо `not_extracted`, если не просмотрел. Эти статусы различать.

| Источники / методы | Где искать и что извлечь | Для каких графиков |
|---|---|---|
| P01/P46; базовые ZCP | Таблицы correlation и runtime; NASLib scores по architecture ID, target labels, seeds, batch, device; полный набор 13 proxies включая `epe_nas`, `grasp`, `grad_norm`, `jacov`, `l2_norm`, `nwot`, `plain`, `snip`, `synflow`, `fisher`, `zen`, `params`, `flops` сверить с версией кода | A, B, D, F |
| P02–P11/P30/P33/P49/P50 | Formula + ablations + timing table; отделить стоимость score, proxy discovery, NAS search и финального обучения; для variants дать отдельные IDs | A, B, C |
| P12 | Appendices C/E/F/M/N: filtered architecture IDs, GRAF features, RF/XGB labels, fitting/query time; Tables 6–8 для остальных datasets; Table 32 — суммарный runtime серии опытов, не runtime кандидата | C, E, F |
| P13 | §5; A.5/A.6/A.8: train sample sizes, transfer source/target, Kendall, encoding generation и fitting time | C, E |
| P14 | Tables 1/2/7, §3.4/4 и Appendix B: IID vs leave-one-dataset-out vs adaptation; percentile label normalization; LM fitting/inference cost | C, E, F |
| P15–P19/P24 | Predictor evaluation tables, head/encoding variants, число H, train/test архитектуры, uncertainty; включить классические RF/XGB/GP/BLR/MLP baselines из общего протокола P24 | C, E |
| P20–P25 | Число epochs/steps, доля полного бюджета, моменты наблюдения LC, финальная target epoch, training schedule; ошибки экстраполяции; цена исторических LC | A, C, E |
| P26 | Rank-correlation plots и определение decoder parameter count; список 200 GPT-2/Transformer-XL архитектур; аппаратные замеры держать отдельно от compute оценки качества | A, D |
| P27 | §4, Appendix A, repository benchmark metadata: 500 архитектур, individual GLUE targets, 100k pretraining steps, ground-truth reliability и CPU proxy times | A, F |
| P28 | Tables 2/3, §4.1, formula appendix, repository: split 50 discovery vs 500/200 evaluation, возможное пересечение, query timings и знак GPT-2 ranking | A, C, F |
| P29 | Tables I/II, §III-D/IV, code при наличии: alpha method для каждой строки; полный runtime scope/device; input-sensitive implementations; расхождения таблиц/текста (§8.7) | A, B, C, F |
| P31 | Полный TPAMI paper, BERT/GLUE subsection: точный proxy, labelled/unlabelled inputs, ранговая корреляция vs только качество найденной модели | A/B после проверки |
| P32 | §IV, Table I, Figures 4/7/8, code: per-task GLUE, размер minibatch, время именно SWAP-Score; regularized vs unregularized | A, B, F |
| P34/P35 | ONNX-Bench/COLE corpora, serialized code lengths, embedding extraction cost, head fitting time, train/test folds; защититься от совпадений architecture IDs и data leakage | C, E |
| P36–P38 | Полный текст/код: входы, seeds, budget accounting; конкретные datasets внутри mean rho; дату/статус preprint | E/F; A только после cost verification |
| P39–P42 | Fitted functions/coefficients, диапазоны N/D/C, фактический calibration compute, held-out scale и prediction error; фиксированы ли данные и recipe | Отдельная scaling-панель |
| P43–P45 | Supernet/hypernetwork training cost, inherited/predicted-weight validation, корреляция с independently trained candidates | A/C только при наличии rank/error validation |
| P47 | Clean vs adversarial objectives, attack/epsilon, RF train size, held-out R², Table 1/2, proxy/GRAF features | Отдельная robustness-панель |
| P48 | Обученные candidate checkpoints, target labels, feature extraction cost, correlation с transfer outcome | Смежная панель, не общий architecture-only ranking |

Открытые маршруты к коду/данным, подтверждённые статьёй либо авторским репозиторием:

| Что | URL | Что брать |
|---|---|---|
| Базовые ZCP | https://github.com/mohsaied/zero-cost-nas | ссылка из P01; реализации scores и reproduction scripts |
| NAS-Bench-Suite-Zero | https://github.com/automl/naslib/tree/zerocost | precomputed scores, targets и общий protocol |
| RNN/BERT training-free | https://github.com/aaronserianni/training-free-nas | метрики и benchmark P27 |
| GRAF | https://github.com/gabikadlecova/zc_combine | features, экспериментальные настройки |
| FLAN | https://github.com/abdelfattah-lab/flan_nas | encodings и predictor experiments |
| Qin surrogates | https://shiwenqin.github.io/TransferrableSurrogate/ | ссылки авторов на код и материалы |
| LPZero | https://github.com/pprp/LPZero | FlexiBERT/GPT-2 proxy implementations |
| SWAP | https://github.com/pym1024/SWAP_Universal | CNN/NLP варианты и benchmark evaluation |
| ONNX-Net | https://github.com/shiwenqin/ONNX-Net | ONNX-Bench и predictor |
| COLE | https://github.com/pcsom/cole/tree/v1.0 | зафиксированный авторами code snapshot |
| NAS-Bench-x11 | https://github.com/automl/nas-bench-x11 | surrogate LC, не реальные новые training runs |
| HAT | https://github.com/mit-han-lab/hardware-aware-transformers | supernet evaluation |
| GHN-2 | https://github.com/facebookresearch/ppuda | predicted weights, DeepNets-1M |

Доступность каждого download проверить локально; «ссылка найдена» не означает «байты скачаны и проверены». Не выдумывать GitHub URL для источников без подтверждённой ссылки. Сначала пройти canonical paper → авторская ссылка. Для данных хранить URL, имя файла, commit/tag, checksum, лицензию и способ сопоставления architecture IDs. Сначала использовать precomputed результаты; воспроизведение обучения требует отдельной задачи пользователя.

### 8.6. Поля, обязательные именно для исследовательского корпуса

Дополнить §7 следующими полями:

| Уровень | Поля |
|---|---|
| Источник | `paper_id`, `title`, `authors`, `first_author_display`, `year_preprint`, `year_publication`, `venue`, `publication_status`, `doi`, `arxiv_id`, `arxiv_version`, `canonical_url`, `pdf_url`, `code_url`, `data_url`, `accessed_at`, `verification_level` |
| Метод | `origin_paper_id`, `evaluation_paper_ids`, `mechanism`, `family_tags`, `method_variant_id`, `component_of`, `priority`, `scope_relation=direct/conditional/adjacent`, `target_architecture_family`, `predictor_architecture_family` |
| Требования | `data_access_at_use`, `input_source`, `label_type`, `weights_state=random/pretrained/inherited/predicted`, `gradient_requirement`, `candidate_training_budget`, `history_labels_required`, `proxy_discovery_required`, `setup_data_requirements` |
| Протокол | `proxy_input_dataset`, `target_train_dataset`, `target_eval_dataset`, `target_metric`, `target_direction`, `target_training_budget`, `search_space_version`, `architecture_ids_hash`, `ground_truth_kind=measured/surrogate/inherited`, `n_discovery`, `n_train_predictor`, `n_eval`, `split_overlap_status` |
| Результат | `raw_metric_value`, `reported_sign_convention`, `oriented_metric_value`, `sign_transform`, `uncertainty_type`, `n_repeats`, `aggregation_scope`, `extraction_status`, `plot_readiness` |
| Затраты | `feature_extraction`, `predictor_fit`, `proxy_discovery`, `label_generation`, `candidate_query`, `search_total`, `final_retraining`, `device`, `precision`, `parallelism`, `batch_size`, `sequence_length`, `measurement_scope`, `accounting_completeness` |
| Доказательства | `source_paper_id`, `source_version`, `locator`, `original_row_label`, `reported_or_derived`, `derivation`, `conflict_id`, `missing_reason` |

`plot_readiness`: `categorical_only`, `metric_only`, `budget_metric`, `cost_metric_provisional`, `cost_metric_verified`. Числа, относящиеся к памяти/latency полученной модели, хранить как `candidate_deployment_cost`, отдельно от стоимости предиктора.

Пример корректной неполной записи, построенный на G1:

```yaml
id: obs_lpzero2024_flexibert_lpzero
method_id: M25
method_variant_id: lpzero_flexibert_reported
evaluation_paper_id: P28
comparison_group_id: lpzero2024_flexibert_t2
domain: nlp_transformer
proxy_input_dataset: OpenWebText
target_eval_dataset: GLUE
target_metric: reported_average_GLUE
target_direction: max
n_eval: 500
metrics:
  - {name: kendall_tau, value: 0.511, extraction_status: reported}
  - {name: spearman_rho, value: 0.748, extraction_status: reported}
candidate_query_cost: null
missing_reason: not_extracted
plot_readiness: metric_only
evidence:
  source_paper_id: P28
  source_version: ACL_official_PDF
  url: https://aclanthology.org/2024.findings-emnlp.502.pdf
  locator: Table 2, printed page 8596, PDF page 5
```

### 8.7. Обнаруженные ограничения и расхождения

Это исследовательские замечания составителя, а не исправления статей.

1. **Origin и evaluation — разные источники.** SynFlow первоначально pruning (P03), а NLP ranking проверяется в P28/P29. Нельзя приписывать исходной статье эксперименты последующих работ.
2. **Не переносить класс по архитектуре предиктора.** M46/M48/M49 используют LM для оценки преимущественно CV-кандидатов. Они R; архитектурные embeddings не являются исследуемыми sentence embeddings.
3. **Версии baseline расходятся.** #params rho: G1=0.590, G2=0.652, G4=0.653. GraSP rho в G1=0.179, тогда как P29 копирует для OpenWebText 0.197. Хранить отдельные source observations; не перезаписывать таблицу P28 значением из P29.
4. **ZeroLM требует проверки конкретного варианта.** Настройка по benchmark labels и heuristic alpha — разные режимы. P29 Table I и текст §IV-B дают немного разные итоговые значения; Table II и §IV-C также расходятся для rho. Для G2 использована таблица; конфликт не устраняется выбором «лучшего» числа.
5. **Data-free не всегда одинаково определено.** Классификация SynFlow как использующего реальные данные в P29 не совпадает с постановкой исходного P03. Нужна запись `implementation_variant`, а не изменение общего свойства метода.
6. **Направление ранжирования.** P29 GPT-2 содержит отрицательные rho к perplexity, P28 — положительные табличные значения. Не применять `abs(rho)`: отрицательный знак может означать и корректную обратную связь, и ошибочное ранжирование. Преобразование разрешено только из определения score/target.
7. **Состав архитектур влияет на сравнение.** P12 исключает unreachable branches. Совпадение имени NB201 не гарантирует одинаковую выборку с P01/P46. NB301/x11 могут давать surrogate ground truth, что требует отдельного признака.
8. **GLUE-average скрывает различия задач.** Не выводить из среднего rank-correlation успешность на retrieval/STS bi-encoders. Per-task результаты импортировать отдельно.
9. **Стоимость обучения benchmark labels нельзя забывать.** Precomputed H бесплатны в текущем запуске инструмента, но их создание не было бесплатным. Показывать два режима учёта: marginal reuse и from-scratch setup; неизвестные historical costs не обнулять.
10. **Числа G5/G7 показывают ценность новой оси.** Для surrogate methods размер размеченной выборки архитектур часто известен лучше полного runtime. Поэтому график label budget → correlation обязателен (§5E).

### 8.8. Границы корпуса и продолжение поиска

Пока не включены как самостоятельные методы все вариации каждого surrogate backbone, все разновидности NAS/weight sharing и все transferability scores. Они импортируются как варианты, если дают новую проверяемую особенность для нашей постановки. Расширять реестр при обнаружении нового механизма, прямого NLP/embedding применения либо сопоставимой экспериментальной таблицы; не увеличивать число точек дубликатами arXiv/conference/journal versions.

Для адресного поиска текстовых эмбеддингов проверять сочетания `architecture performance prediction`, `zero-cost proxy`, `sentence embedding`, `bi-encoder`, `dual encoder`, `retrieval`, `contrastive pretraining`. Фиксировать настоящий embedding objective и retrieval/embedding benchmark. В текущем проходе такого подтверждённого применения не найдено; это ограничение корпуса, не отрицательный результат систематического обзора.

Дополнительные близкие направления уже видны по ссылкам корпуса: MeCo, TA-GATES, BONAS, NAO/SemiNAS, RBFleX-NAS, GHN-3/LoGAH и прогноз downstream performance готовых LLM. Пока это очередь расширения, а не проверенные точки. До добавления нужны canonical paper и подтверждение относимости; не угадывать библиографию из сокращения. EPE-NAS уже зарегистрирован по evaluation-источнику P46; его origin paper остаётся задачей уточнения.


## 9. Локальная реализация: рекомендуемый старт

Сначала осмотреть текущий репозиторий и его инструкции. Если подходящего приложения нет, рабочий вариант — Python, Streamlit и Plotly; окончательный выбор оставить локальному Codex с учётом реального отображения пунктирных круглых маркеров. Для точного контура допустим SVG-компонент. Не создавать лишний серверный стек ради первой версии.

Предлагаемая организация: `app.py`, `data/papers.yaml`, `data/methods.yaml`, `data/observations.yaml`, `schema/`, `README.md`, `exports/`. Можно изменить её, сохранив разделение данных и отображения.

Интерфейс:

- Выбор графика, метрики и вида затрат; фильтры класса, семейства, домена, доступа к данным и группы сопоставимости.
- Hover: origin/evaluation статьи, метод и вариант, эксперимент, исходные значения и знак, единицы, scope затрат, доказательства и статус проверки.
- Карточка статьи по выбору точки; связь с таблицей наблюдений и ссылкой на источник.
- Отдельная таблица работ/наблюдений, не попавших на график, с причиной: нет метрики, нет затрат, не проверено или несовместимый протокол.
- Видимые счётчики: источники по уровню проверки F/A/M, методы, наблюдения по готовности к графикам, отображаемые и исключённые наблюдения. Не считать источник уровня A полностью проверенным численным экспериментом.
- Экспорт текущего графика в SVG/PNG и отфильтрованных данных в CSV. Вместе с экспортом сохранять выбранные фильтры, шкалы, дату и версию корпуса.
- При пустых данных — содержательное пустое состояние; не подставлять демонстрационные точки в исследовательский режим. Синтетические fixtures допустимы только в явно отделённом тестовом режиме.

## 10. Порядок работы локального Codex

1. Прочитать этот файл, инструкции репозитория и имеющиеся материалы. Не предполагать доступ к переписке ChatGPT.
2. Импортировать §8.2–8.3 в отдельные papers/methods данные, сохранив стабильные IDs и уровни проверки. Варианты развернуть без смешения формул. Не превращать весь проверенный корпус обратно в неопределённую очередь.
3. Импортировать G1–G7 и контекстные записи G8 с указанными пропусками и ограничениями; расширить одну строку с несколькими бюджетами в несколько observations. Числа копировать точно, не запускать обучение. Для unresolved method variant G2 сохранить одну временную запись, связанную с кандидатами M26/M27.
4. Реализовать три визуальных класса, легенду с пустым классом эмбеддингов, таблицу методов и карточку источников. Приоритет графиков: D и E доступны сразу; A — с предварительными таймингами G2, строгий режим может быть пуст. Затем B/C/F по готовности полей.
5. При доступе к интернету закрывать конкретные пробелы §8.5. Сначала scope/device таймингов, версия ZeroLM, знак GPT-2 correlation, target G7, setup/query costs. При отсутствии доступа выполнить импорт имеющихся данных и интерфейс; отсутствие новых источников не блокирует весь инструмент.
6. Проверить целостность IDs, нули/пропуски, переключение метрик, sign normalization, разделение протоколов, пунктирные границы и экспорт. Использовать небольшие проверки реальных рисков; оформление проверить визуально.
7. Подготовить README с командой локального запуска и описанием добавления статьи/метода/наблюдения. В отчёте указать импортированные записи, готовность графиков и конкретные оставшиеся пробелы.

## 11. Критерии готовности v0.2

- Приложение запускается локально без GPU и внешнего LLM API.
- Три класса имеют заданный стиль; пустой третий класс остаётся в легенде.
- Все 50 источников и 72 записи методов импортированы; статьи, методы, варианты и результаты связаны идентификаторами. Более мелкое разбиение вариантов допустимо с таблицей соответствия исходным M-ID.
- Численные блоки §8.4 доступны в таблицах и подходящих графиках; объяснено, какие записи ещё не готовы для каждого графика.
- Нет вымышленных чисел, фиктивных ссылок, заполнения неизвестных затрат нулями или неподтверждённых NLP/embedding применений.
- Каждая научная численная точка прослеживается до конкретного места и версии первоисточника; origin и evaluation не смешиваются.
- Шкала около нуля читаема; ноль и отсутствие данных различаются; отрицательные корреляции не превращены автоматически в положительные.
- Несопоставимые результаты не образуют общий рейтинг, тренд или Парето-фронт. SD не подписана как доверительный интервал.
- Бюджет labels, setup, query, NAS search и deployment latency кандидата не смешаны.
- Добавление статьи, метода и наблюдения не требует изменения кода графиков.

## 12. Что дополнить в следующих версиях handoff

- Выбрать конкретный аспект итогового качества текстовых эмбеддингов: retrieval, STS, classification, clustering либо несколько отдельных целей.
- Зафиксировать архитектурные степени свободы и границы неизменного training recipe.
- Уточнить scope/device для затрат и другие помеченные пробелы §8.5–8.7; дополнить сырыми per-architecture scores там, где они опубликованы.
- Разобрать неполное упоминание «Liu» при появлении исходного фрагмента; не считать проблему решённой совпадением фамилии.
- Выполнить отдельный целевой поиск применений к моделям текстовых эмбеддингов; предварительный проход v0.2 не дал подтверждённой записи этого класса.
- После просмотра первого прототипа согласовать приоритет B/C/F и детализацию learning curves/scaling panels.

Журнал изменений:

- v0.1 — восстановленные требования, начальная очередь литературы, модель данных и спецификация локальной визуализации.
- v0.2 — 50 первоисточников, 72 записи методов/вариантов, требования к данным, 8 численных/контекстных блоков, маршруты к коду и точным разделам статей; добавлены E/F, раздельные origin/evaluation ссылки, учёт стоимости discovery/labels и реестр расхождений.
