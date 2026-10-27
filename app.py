import io, json, zipfile
from collections import Counter
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from corpus import load, flatten, csv_bytes, eligible, access, ROOT
from charts import chart, map_chart, export, interactive_svg, METRICS, ACCESS
st.set_page_config(page_title='Качество архитектуры',layout='wide')
papers=load('papers'); methods=load('methods'); obs=load('observations'); manifest=load('manifest')
pm={p['id']:p for p in papers}; mm={m['id']:m for m in methods}
st.title('Предсказание качества архитектуры')
st.caption('Исследовательский корпус v0.2 · численные результаты авторов · 29.09.2026')
st.write('Фиксированы данные и протокол обучения; меняется архитектура. Корреляция оценивает согласованность ранжирования, а не процент точных прогнозов.')
cols=st.columns(4)
cols[0].metric('Источники',len(papers)); cols[1].metric('Методы',len(methods)); cols[2].metric('Наблюдения',len(obs)); cols[3].metric('Text embedding',sum(m['visual_class']=='text_embedding' for m in methods))
st.caption('Уровни источников из handoff: '+str(dict(Counter(p['verification_level'] for p in papers)))+'. F - просмотр частей полного текста; A - abstract; M - библиография. Это не воспроизведение эксперимента.')
st.caption('Готовность наблюдений: '+str(dict(Counter(o['plot_readiness'] for o in obs))))
with st.sidebar:
    view=st.selectbox('Представление',['D · Карта методов','E · Бюджет меток','A · Время оценки','B · Доступ к данным','C · Setup / новый кандидат','F · Раздельные протоколы','Численные результаты','Каталог источников'])
    classes=st.multiselect('Класс метода / домен наблюдения',['relevant','nlp_transformer','text_embedding','unknown'],default=['relevant','nlp_transformer','text_embedding','unknown'])
    families=st.multiselect('Семейства',sorted({f for m in methods for f in m['family_tags']}))
    accesses=st.multiselect('Доступ к данным при применении',list(ACCESS),format_func=lambda a:ACCESS[a].replace('\n',' '))
    st.caption('Training-free, data-free и отсутствие обучаемого предиктора - разные свойства. Метки качества для setup могут требоваться даже при data-free применении.')
selected_methods=[m for m in methods if m.get('analysis_status')!='excluded' and (m['visual_class'] or 'unknown') in classes and (not families or set(m['family_tags'])&set(families)) and (not accesses or m['data_access_at_use'] in accesses)]
selected_ids={m['id'] for m in selected_methods}
selected_obs=[o for o in obs if o['domain'] in classes and (not families or any(f in families for mid in ([o['method_id']] if o['method_id'] else o['method_candidates']) for f in mm[mid]['family_tags'])) and (not accesses or access(o,mm) in accesses)]
fig=None; displayed=[]; plot=view[0]; metric_name='spearman_rho'; group=None; provisional=False; scale='linear'; linthresh=.5; zoom=None
if plot=='D':
    fig,displayed=map_chart(selected_methods)
    st.caption('Аудит 13.10.2026: 69 методов включены; M28, M40, M72 исключены. Требования привязаны к варианту. InTrain проверен по полному тексту.')
elif view=='Каталог источников':
    st.dataframe(pd.DataFrame(papers)[['id','title','first_author_display','verification_level','canonical_url']],hide_index=True)
else:
    metric_name=st.sidebar.selectbox('Метрика',list(METRICS),format_func=lambda x:METRICS[x],index=1 if plot=='E' else 0)
    if plot=='F':
        st.info('Раздельные панели источников: различия нельзя приписать только входному датасету. Controlled comparisons пока не извлечены.')
        groups=st.multiselect('Протоколы для просмотра',list(dict.fromkeys(o['comparison_group_id'] for o in selected_obs)),default=[g['id'] for g in load('groups') if g['block'] in ['G1','G2','G4'] and any(o['comparison_group_id']==g['id'] for o in selected_obs)])
        for g in groups:
            oo=[o for o in selected_obs if o['comparison_group_id']==g]
            ff,dd=chart(oo,name=metric_name,title=g)
            st.iframe(interactive_svg(ff,dd),height=650)
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
                for fmt in ['svg','png','pdf']: z.writestr('chart.'+fmt,export(ff,fmt))
                z.writestr('data.csv',csv_bytes(dd))
                z.writestr('selection.json',json.dumps(dict(view=view,group=g,metric=metric_name,classes=classes,families=families,accesses=accesses,scale='linear',corpus=manifest,generated_at=datetime.now(timezone.utc).isoformat()),ensure_ascii=False,indent=2))
            st.download_button('Экспорт панели '+g,archive.getvalue(),g+'.zip','application/zip',key=g)
            plt.close(ff); displayed+=dd
    else:
        groups=list(dict.fromkeys(o['comparison_group_id'] for o in selected_obs))
        preferred=next((g for g in groups if ('graf2024' if plot=='E' else 'zerolm2025' if plot=='A' else 'lpzero2024_flexibert') in g),None)
        group=st.sidebar.selectbox('Группа сопоставимости',groups,index=groups.index(preferred) if preferred else 0) if groups else None
        oo=[o for o in selected_obs if o['comparison_group_id']==group]
        if plot=='A':
            provisional=st.sidebar.checkbox('Показать предварительные тайминги',value=False)
            st.sidebar.selectbox('Вид затрат',['Reported average time, s'])
            scale=st.sidebar.selectbox('Шкала X',['linear','symlog'])
            linthresh=st.sidebar.number_input('Линейная область symlog, s',min_value=.001,value=.5)
            if st.sidebar.checkbox('Увеличить область около нуля'): zoom=st.sidebar.number_input('Правая граница X, s',min_value=.01,value=1.0)
            st.warning('Полный учёт стоимости и аппаратура G2 не подтверждены. Строгий режим пуст. ZeroLM* - одна запись с неустановленным вариантом M26/M27. Парето выключен.')
            st.caption('Полное обучение + бенчмарк: численный baseline отсутствует. Условное совпадение с эталоном не является измеренной точностью.')
        if plot=='C':
            st.info('C_total(N) = C_setup + N × C_candidate применим только к совместимым, неперекрывающимся затратам. Таких пар пока нет; неизвестные компоненты не заменены нулями. Для active learning линейный расчёт не включён.')
        fig,displayed=chart(oo,plot if plot in ['A','B','C','E'] else 'metric',metric_name,scale,linthresh,provisional,mm,title=group or 'Нет выбранной группы',zoom=zoom)
        if group:
            g=next((g for g in load('groups') if g['id']==group),None)
            if g: st.caption(g['notes'])
if fig:
    st.iframe(interactive_svg(fig,displayed),height=880 if plot=='D' else 650)
    st.caption('Наведите на круг для исходной записи; клик откроет карточку в новой вкладке. Карточку также можно выбрать ниже.')
    config=dict(view=view,metric=metric_name,group=group,classes=classes,families=families,accesses=accesses,provisional=provisional,scale=scale,linthresh_seconds=linthresh,zoom_max_seconds=zoom,generated_at=datetime.now(timezone.utc).isoformat(),corpus=manifest,displayed_ids=[o['id'] for o in displayed])
    csv=csv_bytes(displayed) if plot!='D' else pd.DataFrame(displayed).to_csv(index=False).encode('utf-8-sig')
    files={'chart.svg':export(fig,'svg'),'chart.png':export(fig,'png'),'chart.pdf':export(fig,'pdf'),'data.csv':csv,'selection.json':json.dumps(config,ensure_ascii=False,indent=2).encode()}
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,b in files.items(): z.writestr(name,b)
    st.download_button('Экспорт графика, данных и параметров (ZIP)',archive.getvalue(),'architecture-selection.zip','application/zip')
    plt.close(fig)
report=ROOT/'output/pdf/architecture_quality_report.pdf'
if report.exists(): st.download_button('Полный PDF-отчёт',report.read_bytes(),report.name,'application/pdf')
st.write(f'Отображено: {len(displayed)}. Исключено из текущего графика: {(len(methods) if plot=="D" else len(obs))-len(displayed)}.')
if plot=='D':
    st.dataframe(pd.DataFrame(selected_methods).reindex(columns=['id','name','visual_class','data_access_at_use','requirements_raw']),hide_index=True)
    st.dataframe(pd.DataFrame([dict(id=m['id'],reason=m.get('access_review',{}).get('reason','фильтр')) for m in methods if m['id'] not in {d['id'] for d in displayed}]),hide_index=True)
else:
    st.dataframe(pd.DataFrame(flatten(displayed)),hide_index=True)
    displayed_ids={o['id'] for o in displayed}; selected_obs_ids={o['id'] for o in selected_obs}
    excluded=[dict(id=o['id'],method=o['method_id'],group=o['comparison_group_id'],reason='фильтр класса / семейства / данных' if o['id'] not in selected_obs_ids else 'другая группа сопоставимости' if group and o['comparison_group_id']!=group else eligible(o,plot,metric_name,provisional) or ('за пределами увеличенной области' if plot=='A' and zoom is not None else 'не выбрана панель')) for o in obs if o['id'] not in displayed_ids]
    with st.expander('Исключённые наблюдения и причины'): st.dataframe(pd.DataFrame(excluded),hide_index=True)
with st.expander('Контекстные затраты (не полная стоимость кандидата)'): st.dataframe(pd.DataFrame(load('context')),hide_index=True)
st.subheader('Карточка метода / наблюдения')
all_ids=[o['id'] for o in obs]+[m['id'] for m in methods]
requested=st.query_params.get('observation')
selected=st.selectbox('Запись',all_ids,index=all_ids.index(requested) if requested in all_ids else 0)
record=next((o for o in obs if o['id']==selected),None)
if record:
    st.json(record)
    related=[mm[mid] for mid in ([record['method_id']] if record['method_id'] else record['method_candidates'])]
else: related=[mm[selected]]
for method in related:
    st.write(method['id']+' · '+method['name']); st.json(method)
    ids=list(dict.fromkeys(([method['origin_paper_id']] if method['origin_paper_id'] else [])+method['evaluation_paper_ids']+([record['evaluation_paper_id']] if record else [])))
    for pid in ids:
        p=pm[pid]
        st.markdown(f"[{pid}: {p['title']}]({p['canonical_url']})")
        st.caption(p['bibliography_raw']+' | уровень '+p['verification_level'])
    st.dataframe(pd.DataFrame(flatten([o for o in obs if o['method_id']==method['id'] or method['id'] in o['method_candidates']])),hide_index=True)
with st.expander('Карточка любого источника'):
    pid=st.selectbox('Источник',list(pm)); st.json(pm[pid])
