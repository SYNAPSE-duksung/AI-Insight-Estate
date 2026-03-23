# Roadview-Urban-Analytics

Roadview-Urban-Analytics는 서울시 상권 분석 데이터의 급격한 변화 시점(매출 급상승/하락)을 포착하고, 해당 시점 전후의 로드뷰(Roadview) 이미지를 분석하여 상권 변화의 실질적인 원인을 추론하고, 더 나아가서는 앞으로의 상권 전망을 예측하는 분석 프레임워크입니다.

📌 Project Overview
단순히 과거 데이터를 나열하는 것을 넘어, 상권의 변화 이유를 거리의 시각적 변화에서 찾습니다.

Change Point Detection: 상권 매출 및 공실률 데이터에서 유의미한 변곡점(T-Point) 추출
Visual Evidence Harvest: 변곡점 전후 1~2년의 로드뷰 데이터 수집 및 비교
Computer Vision Inference: ViT(Vision Transformer) 및 Segmentation 모델을 활용한 주요 지표(통유리 면적, 셔터 노출 등) 수치화
Urban Insight: 시각적 변화와 경제 지표 간의 상관관계 분석 및 상권 변화 지수 산출

🛠️ Key Process
1. Data-Driven Pivot (데이터 기반 변곡점 탐색)
서울시 상권분석 서비스 API를 활용한 시계열 데이터 분석
매출 급성장 지역(성수, 용리단길 등)과 쇠퇴 지역(이대, 경리단길 등)의 대조군 설정

2. Roadview Chronology (시계열 로드뷰 아카이빙)
특정된 변곡점을 기준으로 시계열 거리뷰 데이터 크롤링 및 정렬
동일 위치, 다른 시점의 이미지를 정규화하여 분석 환경 구축

3. Visual Hypothesis & AI (시각적 가설 검증)
육안 분석을 통한 가설 설정 (예: "통유리 인테리어의 증가가 매출 상승과 상관관계가 있는가?")
Segmentation 모델을 통한 객체별 점유 면적 및 변화량 자동 산출
