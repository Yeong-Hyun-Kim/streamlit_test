import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib
import platform

# 한글 폰트 설정
if platform.system() == 'Windows':
    matplotlib.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin':  # macOS
    matplotlib.rc('font', family='AppleGothic')
else:  # Linux/Streamlit Cloud
    matplotlib.rc('font', family='NanumGothic')  # 따로 설치 필요

plt.rcParams['axes.unicode_minus'] = False


# 한글 설정 및 페이지 설정
st.set_page_config(page_title="시니어 마이데이터 분석 및 예적금 유도", layout="wide")
st.title("💳 시니어 마이데이터 고객 분석 + 예·적금 제안 대시보드")

# --- 데이터 로드 및 전처리 ---
df = pd.read_csv("streamlit_test\sss.csv")

# 월수령연금 계산 (연금 총액을 12개월로 나눔)
df['월수령연금'] = df['연금'] / 12

# 총지출 계산
spending_cols = [
    '간편결제/충전','외식','온라인쇼핑','교육','술/유흥','배달',
    '카페/디저트','교통/자동차','취미/여가','편의점/마트','생활비',
    '쇼핑','건강/뷰티','주거/세금','의료','출금/이체','기타'
]
df['월지출_총액'] = df[spending_cols].sum(axis=1)

# 묶여있는 돈: 예금 + 적금 (현금성 자산만)
df['묶여있는_돈'] = df['예금'] + df['적금']

# 펀드 평가손익 별도 컬럼
df['펀드_평가손익'] = df['펀드']

# 여유자금: 월수입+월수령연금 - 월지출
if '월수입_총액' in df.columns:
    df['여유자금'] = df['월수입_총액'] + df['월수령연금'] - df['월지출_총액']
else:
    df['여유자금'] = df['월수령연금'] - df['월지출_총액']

# --- 대시보드 ---
st.subheader("👤 고객 선택")
if '이름' in df.columns:
    customer = st.selectbox("고객 이름 선택", df['이름'].unique())
    cust = df[df['이름'] == customer].iloc[0]

    # KPI: 5개 지표로 확장
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("💰 묶여있는 돈", f"{int(cust['묶여있는_돈']):,} 원")
    col2.metric("📈 월수령 연금", f"{int(cust['월수령연금']):,} 원")
    col3.metric("💸 월지출", f"{int(cust['월지출_총액']):,} 원")
    col4.metric("🪴 여유자금", f"{int(cust['여유자금']):,} 원")
    col5.metric("💼 펀드 평가손익", f"{int(cust['펀드_평가손익']):,} 원")

    # 여유자금 기반 상품 추천
    st.subheader("💡 여유자금 기반 상품 추천")
    if cust['여유자금'] >= 0:
        st.success(
            f"{customer}님 여유자금 {int(cust['여유자금']):,}원 양호.\n"
            "→ 단·중기 자유적립식 적금, 정기예금 등 자산 증식 상품 제안"
        )
    else:
        st.warning(
            f"{customer}님 매월 {abs(int(cust['여유자금'])):,}원 부족.\n"
            "→ 생활비 안심대출, 자금관리형 상품 권장 및 지출 패턴 점검 상담"
        )

    # 여유자금 게이지
    st.subheader("🪴 여유자금 현황")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=cust['여유자금'],
        delta={'reference': df['여유자금'].mean()},
        gauge={
            'axis': {'range': [df['여유자금'].min(), df['여유자금'].max()]},
            'steps': [
                {'range': [df['여유자금'].min(), df['여유자금'].mean()], 'color': "#F5A9A9"},
                {'range': [df['여유자금'].mean(), df['여유자금'].max()], 'color': "#81BEF7"},
            ],
            'bar': {'color': 'green'}
        },
        title={'text': f"{customer}님의 여유자금 위치"}
    ))
    st.plotly_chart(fig, use_container_width=True)

    # 카테고리별 소비 비중
    st.subheader("🍽️ 카테고리별 소비 비중")
    spend = cust[spending_cols].sort_values(ascending=False)
    fig_sp = px.bar(x=spend.index, y=spend.values, text_auto=True,
                    labels={'x':'카테고리','y':'지출'})
    st.plotly_chart(fig_sp, use_container_width=True)

    # 타인 평균 대비 지출 비교
    st.subheader("📊 타인 평균 대비 지출 비교")
    others = df[df['이름'] != customer][spending_cols].mean()
    diff = pd.DataFrame({'카테고리':spending_cols,
                         '차이':cust[spending_cols].values - others.values})
    fig_cmp = px.bar(diff, x='카테고리', y='차이',
                     color=diff['차이']>0, labels={'차이':'고객-타인 평균'}, text='차이')
    st.plotly_chart(fig_cmp, use_container_width=True)

    # 분석 결과 다운로드: pandas.concat 사용
    result_summary = pd.DataFrame({
        '지표': ['묶여있는 돈','월수령연금','월지출','여유자금','펀드 평가손익'],
        '값': [cust['묶여있는_돈'], cust['월수령연금'], cust['월지출_총액'], cust['여유자금'], cust['펀드_평가손익']]
    })
    diff_download = diff.rename(columns={'차이':'값'})[['카테고리','값']]
    diff_download = diff_download.rename(columns={'카테고리':'지표'})
    download_df = pd.concat([result_summary, diff_download], ignore_index=True)
    csv = download_df.to_csv(encoding='utf-8-sig', index=False)
    st.download_button("📥 분석 데이터 다운로드", csv, file_name=f"{customer}_분석.csv")

else:
    st.error("⚠️ '이름' 컬럼이 없어 고객 선택이 불가합니다.")

# 원본 데이터 확인
with st.expander("🔍 원본 데이터 확인"):
    st.dataframe(df)
