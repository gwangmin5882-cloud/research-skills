이 폴더의 manuscript.md는 논문 서론 초안이야. 참고문헌 10개가 실제로 있는 문헌인지, 서지 정보가 맞는지, 그리고 본문에서 각 문헌을 인용한 내용이 그 문헌과 맞는지 확인해줘.

결과는 이 폴더에 verdicts.csv 로 저장해줘. 열은 ref, existence, claim, note 네 개야.
- ref: 참고문헌 번호 (예: 1)
- existence: OK / WRONG_METADATA / WRONG_ID / FAKE / UNSURE 중 하나
  - OK: 실제로 있고 서지 정보도 맞음
  - WRONG_METADATA: 문헌은 있지만 저자·연도 등 정보가 틀림
  - WRONG_ID: DOI나 arXiv 번호가 다른 문헌을 가리킴
  - FAKE: 존재하지 않는 문헌으로 판단
  - UNSURE: 판단할 수 없음
- claim: SUPPORTED / PARTIAL / NOT_SUPPORTED / CANT_TELL / NA 중 하나 (문헌이 없거나 확인할 수 없으면 NA)
- note: 판단 근거 한 줄

그리고 나에게 결과를 짧게 요약해줘.
