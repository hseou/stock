import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import feedparser
import ollama
import urllib.parse
import requests

# 1. 페이지 설정 및 용어 사전
st.set_page_config(page_title="주린이 AI 가이드", layout="wide")

DICT_TERMS = {
    "PER": "주가수익비율: 회사가 버는 돈에 비해 주가가 비싼지 싼지 알려줘요. (낮을수록 저평가)",
    "ROE": "자기자본이익률: 내 돈으로 얼마나 알차게 수익을 냈는지 보여주는 성적표예요. (높을수록 좋음)",
    "Market Cap": "시가총액: 이 회사를 통째로 사려면 필요한 돈이에요."
}

def get_safe_news(query):
    try:
        safe_name = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={safe_name}+stock&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(url)
        return [{"title": entry.title, "link": entry.link} for entry in feed.entries[:5]]
    except: return []

# --- 메인 UI ---
st.title("🐣 주린이 AI 주식 가이드")
st.write("기업 이름만 입력하면 후보를 보여드리고, 선택하신 기업을 분석해 드려요.")

# 2. 기업 검색 입력
search_query = st.text_input("🔍 분석하고 싶은 회사 이름을 입력하세요 (예: 삼성전자, 애플, 테슬라)")

if search_query:
    try:
        # 야후 파이낸스 검색 API 호출
        search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(search_query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers).json()
        quotes = response.get("quotes", [])

        if not quotes:
            st.error("검색 결과가 없습니다. 이름을 다시 확인해 주세요.")
        else:
            # 3. 후보군 리스트 생성
            options = {}
            for q in quotes:
                # 이름(티커) - 거래소 형태
                name = q.get('longname', q.get('shortname', 'Unknown'))
                symbol = q.get('symbol')
                exch = q.get('exchDisp', 'Etc')
                display_text = f"{name} ({symbol}) - {exch}"
                options[display_text] = symbol

            # 4. 사용자 선택 (셀렉트박스)
            selected_display = st.selectbox("찾으시는 기업이 아래 리스트에 있나요? 선택해 주세요:", options.keys())
            target_ticker = options[selected_display]

            # 5. 분석 시작 버튼
            if st.button(f"🚀 {target_ticker} 분석 시작하기"):
                stock = yf.Ticker(target_ticker)
                info = stock.info

                if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                    st.error("죄송합니다. 이 종목의 상세 재무 데이터를 가져올 수 없습니다.")
                else:
                    company_name = info.get('longName', target_ticker)
                    st.divider()
                    st.header(f"📊 {company_name} 분석 결과")

                    # 섹션 1: 핵심 지표 (Metrics)
                    col1, col2, col3 = st.columns(3)
                    price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
                    col1.metric("현재 주가", f"{price} {info.get('currency', 'USD')}")
                    
                    per = info.get('trailingPE', 'N/A')
                    col2.metric("PER (수익성)", per, help=DICT_TERMS["PER"])
                    
                    roe = info.get('returnOnEquity', 0)
                    col3.metric("ROE (효율성)", f"{roe*100:.2f}%" if roe else "N/A", help=DICT_TERMS["ROE"])

                    # 섹션 2: 그래프 & 뉴스
                    mid1, mid2 = st.columns([2, 1])
                    with mid1:
                        st.write("📈 **최근 6개월 주가 추이**")
                        hist = stock.history(period="6mo")
                        if not hist.empty:
                            fig, ax = plt.subplots(figsize=(10, 4))
                            ax.plot(hist.index, hist['Close'], color='#1f77b4', linewidth=2)
                            ax.grid(True, alpha=0.3)
                            st.pyplot(fig)

                    with mid2:
                        st.write("📰 **최근 관련 뉴스**")
                        news_list = get_safe_news(company_name)
                        news_summary = ""
                        for n in news_list:
                            st.markdown(f"• [{n['title']}]({n['link']})")
                            news_summary += n['title'] + ". "

                    # 섹션 3: AI 분석
                    st.divider()
                    st.subheader("🤖 AI 성장 가능성 예측 리포트")
                    with st.spinner("AI가 분석 중입니다..."):
                        prompt = f"""
                        당신은 주식 초보자를 위한 친절한 멘토입니다. {company_name} 주식을 분석하세요.
                        지표: PER {per}, ROE {roe}
                        뉴스 요약: {news_summary}
                        
                        1. 이 회사가 정확히 무엇을 하는 회사인지 주린이 눈높이에서 설명.
                        2. 위 지표와 뉴스를 볼 때 성장 가능성이 있는지 분석.
                        3. 투자 의견(매수/보류/매도)과 그 이유를 아주 쉽게 설명해줘.
                        """
                        try:
                            res = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}])
                            st.info(res['message']['content'])
                        except Exception as e:
                            st.error(f"AI 분석 실패: {e}")

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
