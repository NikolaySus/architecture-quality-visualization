"""Curated decisions; source corpus remains immutable, overlay is reproducible."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows=[]
def resolved(mid,pid,access,scope,use,setup,locator):
 rows.append(dict(method_id=mid,status='resolved',paper_id=pid,data_access_at_use=access,variant_scope=scope,use_requirements=use,setup_requirements=setup,locator=locator))
def excluded(mid,pid,reason,locator):
 rows.append(dict(method_id=mid,status='excluded',paper_id=pid,reason=reason,locator=locator))
R=resolved
R('M13','P06','unlabeled','TE-NAS, исходный CV-протокол','Реальные изображения без меток; случайные веса; NTK и linear regions.','Подготовка архитектур; обучение предиктора на H не требуется.','Appendix A, technical details')
R('M16','P09','unlabeled','FreeREA aggregate','Реальный batch для linear regions; синтетический вход LogSynflow; skip count.','Эволюционный поиск; отдельного обученного предиктора нет.','§3.1–3.1.1')
R('M18','P11','none','AZ-NAS, опубликованный протокол','Случайные веса и Gaussian input; реальные данные и метки не нужны.','Фиксированная агрегация четырёх proxies.','§3; §4 experimental settings')
for mid,scope in [('M19','DSS / TF-TAS, исходный ViT'),('M20','DSS: synaptic diversity, исходный ViT'),('M21','DSS: synaptic saliency, исходный ViT')]:
 R(mid,'P30','none',scope,'Случайные веса; искусственный вход из единиц. NLP-адаптации сюда не перенесены.','Обучение по историческим качествам для формулы не требуется.','§3.2–3.4, implementation')
R('M31','P33','labeled_or_objective','ParZC с loss-based node-wise статистиками','Batch X и целевая функция для градиентных статистик (включая Fisher/GradNorm).','MABN обучается по историческим качествам архитектур; DiffKendall.','§3.1–3.3; Appendix, node-wise statistics')
R('M34','P50','unlabeled','WRCor voting: SJW и SPW','Реальный batch без меток для WRCor/JacCor/PNorm; SynFlow — синтетический вход.','Фиксированное голосование; не смешивать с baseline SynFlow+JacCor+SNIP.','§3.3.3')
R('M35','P36','none','InTrain, опубликованный CV-протокол','Gaussian input и случайные targets; градиентный расчёт не требует реальных меток.','Фиксированная оценка geometry и gradient health; без обучения кандидата.','§3.2–3.3; §4.1–4.2')
for mid in ['M37','M38','M39']:
 R(mid,'P12','labeled_or_objective','Полный набор 13 ZCP; RF / XGB, с GRAF либо без','Для нового кандидата получение ZCP включает X и loss/targets; GRAF — признаки графа.','H для обучения RF/XGB. Готовый benchmark кэширует затраты получения ZCP.','§3; Appendix C.3, список 13 ZCP')
R('M50','P37','labeled_or_objective','ZAPS, набор 13 ZCP','Получение полного ZCP-вектора требует X и loss/targets; топология G.','Offline H для ProxyFit; затем активное получение качеств выбранных кандидатов.','§3 ProxyFit; §4.1 proxies')
for mid,setup in [('M51','Фиксированный rank prior и target-free gate; качества архитектур не нужны для gate.'),('M52','Обучение anchors на малом бюджете и validation-кривые; подгонка residual model. Полное обучение всех кандидатов не требуется.')]:
 R(mid,'P38','unlabeled','CoRA, NB101/NB201/NATS-SSS classification','Реальный batch без меток для jacov; остальные признаки графовые/синтетические. TransNAS с synthetic input — другой вариант.',setup,'§3.2–3.3; §5 limitations')
R('M53','P20','labeled_or_objective','Baker learning-curve SVR','Частичное обучение кандидата и validation-кривая; признаки конфигурации.','Исторические кривые и финальные качества для SVR.','§3.1')
R('M54','P21','none','LC-Net: предсказание по конфигурации x и эпохе t','Конфигурация и номер эпохи; частичная кривая нового кандидата не является входом сети.','Обучение на кривых других конфигураций; получение кривых требует данных и objective.','§2.4, Eq.7; §3.3, footnote 2')
R('M55','P22','labeled_or_objective','Domhan probabilistic extrapolation','Частичное обучение кандидата и validation-кривая.','Подгонка смеси параметрических кривых к наблюдениям кандидата; H других архитектур не обязателен.','§2–3, predictive termination criterion')
R('M57','P25','labeled_or_objective','NAS-Bench-x11: LCE framework WPM/LcSVR','Короткие прогоны кандидатов и validation-качества.','WPM подгоняется к текущей кривой; LcSVR дополнительно учится на исторических кривых.','§4, Algorithm 2')
R('M58','P24','labeled_or_objective','OMNI с SoTL-E и Jacobian covariance','Частичное обучение для SoTL-E, loss и реальные входы; архитектурная кодировка.','Исторические пары для SemiNAS/NGBoost; здесь рассматривается полный гибрид.','§4.1, Omnipotent Predictor')
for mid,pid,scope,loc in [('M59','P39','Kaplan: fitted scaling relation','§3, empirical scaling laws'),('M60','P40','Chinchilla: параметрическая модель L(N,D)','§3.3, Approach 3'),('M61','P41','Tay: зависимости для фиксированного семейства архитектур','§5.3, Table 2'),('M62','P42','Dense/MoE: fitted L(N,D,E)','§4.1–4.2, Eq.5')]:
 R(mid,pid,'none',scope,'Размер/ресурсные параметры и выбранное семейство; реальные примеры при подстановке в fitted relation не нужны.','Калибровочные обучения на текстах и измеренные losses/качества. Перенос за область калибровки не подтверждён.',loc)
R('M63','P43','labeled_or_objective','HAT inherited-weight quality evaluation','Наследованные веса и validation-пары перевода для оценки loss.','Обучение supernet на параллельных текстах; hardware latency predictor отдельно.','§2.2–2.3; §3')
R('M64','P44','labeled_or_objective','AutoTinyBERT search evaluator','Подмодели SuperPLM; оценка на SQuAD и MNLI с целевыми ответами.','Обучение SuperPLM; отдельный предиктор latency на измеренных временах.','§3.5, Search Process')
R('M65','P45','labeled_or_objective','GHN-2: оценка качества по предсказанным весам','Предсказанные веса; изображения и метки для accuracy. Регрессия по graph embeddings — отдельный механизм.','Обучение GHN на архитектурах и задачах классификации.','Appendix C.2.3, Estimating properties by predicting parameters')
R('M67','P47','labeled_or_objective','RF clean/robustness: все ZCP, с GRAF либо без','Полный ZCP-вектор требует X и loss/targets; perturbed-input вариант также требует генерации атак.','Исторические clean/robustness accuracies для обучения RF.','§4.2, Tables 1–3; Tables 6–7')
R('M71','P01','labeled_or_objective','Plain: сумма weight × gradient','Случайные веса, реальные входы и градиент loss.','Историческое обучение предиктора не требуется.','Zero-cost proxies, baseline plain; P46 Table 1')
excluded('M15','P08','Запись «discovered proxy» не фиксирует EZNAS-A/B или NLP-адаптацию. Их входные тензоры различаются; привязка конкретной формулы не завершена.','§3, Figure 1; §8, найденные программы')
excluded('M23','P27','Название объединяет варианты head/attention importance. Не закреплены точная формула и loss для NLP-строк корпуса; origin не заменяет проверку адаптации.','P27; P28 Table 1, адаптированные proxies')
excluded('M25','P28','Для записи найденной формулы не завершена привязка к исполняемому выражению и его входам; требования search space не равны требованиям найденной формулы.','§3; приложение с найденными формулами')
excluded('M28','P31','Полный текст не получен: DOI не вернул содержимого, авторское зеркало недоступно из-за сертификата. Abstract не устанавливает состав входов evaluation proxy.','DOI 10.1109/TPAMI.2024.3378781; авторское зеркало JDL')
excluded('M40','P13','FLAN допускает graph-only и дополнительные CATE/Arch2Vec/ZCP encodings с разными требованиями. Исходная строка не фиксирует вариант, к которому относятся её затраты.','§4.3; Appendix A.5')
excluded('M72','P46','Подтверждена зависимость EPE-NAS от данных, но проверка class-wise реализации и точного использования targets не завершена; двоичного data-dependent флага недостаточно.','Table 1–2; ссылка [20]')
rows[:]=[r for r in rows if r['method_id'] not in ['M15','M23','M25']]
R('M15','P28','unlabeled','EZNAS: Electra/FlexiBERT реализация LPZero','Реальные тексты; backward от суммы hidden states, без task labels.','Поиск формулы использует исторические качества; GPT-2 ветвь требует отдельной классификации.','lpzero/predictor/measures/eznas.py: compute_eznas')
R('M23','P28','unlabeled','Head importance: Electra/FlexiBERT реализация LPZero','Реальные тексты; градиент суммы hidden states; weight × gradient.','Отдельный predictor fit для применения фиксированной формулы не нужен.','lpzero/runner/eval_rank_bert.py:154–175; attention_head_importance.py')
R('M25','P28','unlabeled','LPZero: найденная FlexiBERT формула head + act','Реальные тексты; head/activation tensors; targets не используются.','Эволюционный поиск формулы по историческим GLUE-качествам.','lpzero/runner/eval_searched_bert.py:263–272; operators/zc_inputs.py')
downloads={r['paper_id']:r for r in json.loads((ROOT/'data/source_audit/downloads.json').read_text())}
papers={r['id']:r for r in json.loads((ROOT/'data/papers.json').read_text())}
for r in rows:
 d=downloads.get(r['paper_id'],{});r.update(reviewed_on='2026-10-13',url=d.get('requested_url',papers[r['paper_id']]['canonical_url']),source_version=d.get('source_version','bibliographic_record'),source_sha256=d.get('sha256'),evidence_type='primary_source_review' if r['status']=='resolved' else 'insufficient_evidence')
commit='876432761a2ff67a77194018ebc88bdc42869974'
for r in rows:
 if r['method_id'] in ['M15','M23','M25','M71']:
  path={'M15':'lpzero/predictor/measures/eznas.py','M23':'lpzero/runner/eval_rank_bert.py','M25':'lpzero/runner/eval_searched_bert.py','M71':'lpzero/predictor/measures/plain.py'}[r['method_id']]
  r.update(url=f'https://github.com/pprp/LPZero/blob/{commit}/{path}',source_version=commit,evidence_type='author_implementation_review',source_sha256=None)
rows.sort(key=lambda r:r['method_id'])
assert len(rows)==35 and len({r['method_id'] for r in rows})==35
(ROOT/'data/access_audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print({s:sum(r['status']==s for r in rows) for s in ['resolved','excluded']})
