"""第七课：向量检索 vs 关键词检索 — 对比实验"""

import chromadb

# ---- 准备文档 ----
docs = [
    "如何申请退款：在订单页面点击申请售后即可",
    "退货流程：填写退货原因后等待审核通过",
    "公司地址在北京市海淀区中关村",
    "我们的产品支持七天无理由退换",
]

# ---- 1. 关键词检索（老办法） ----
def keyword_search(query, docs):
    results = []
    for d in docs:
        score = sum(1 for w in query if w in d)
        results.append((score, d))
    results.sort(key=lambda x: x[0], reverse=True)
    return results

# ---- 2. 向量检索（新办法） ----
client = chromadb.Client()
collection = client.create_collection("demo")
for i, d in enumerate(docs):
    collection.add(documents=[d], ids=[str(i)])

def vector_search(query):
    r = collection.query(query_texts=[query], n_results=2)
    return list(zip(r["distances"][0], r["documents"][0]))

# ---- 测试 ----
print("=" * 50)
print('搜索: 退钱（文档里没有退钱这个词）')
print("=" * 50)

print('\n【关键词检索】搜"退钱"：')
for score, d in keyword_search("退钱", docs):
    print(f"  命中{score}个词 → {d}")

print('\n【向量检索】搜"退钱"：')
for dist, d in vector_search("退钱"):
    print(f"  距离{dist:.3f} → {d}")
