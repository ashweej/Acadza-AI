import os
import glob
import datetime as dt
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


def load_documents():
    documents = []
    for file in glob.glob("documents/*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                documents.append(content)
    for file in glob.glob("documents/*.pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(file) as pdf:
                text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                if text.strip():
                    documents.append(text.strip())
        except Exception as e:
            print(f" Could not read {file}: {e}")
    return documents


retriever_model = SentenceTransformer("all-MiniLM-L6-v2")


hf_model = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(hf_model)
model = AutoModelForSeq2SeqLM.from_pretrained(hf_model)


def generate_answer_local(context, query, now_str):
    prompt = f"""
    You are a helpful assistant.
    Current date & time: {now_str}
    Use the context below to answer the question.

    Context:
    {context}

    Question: {query}
    """

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    outputs = model.generate(**inputs, max_length=300)
    return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()



def answer_query(query, corpus, retriever_model, tz_offset_hours=0):
    # Get datetime
    now_utc = dt.datetime.now(dt.timezone.utc)
    now_local = now_utc + dt.timedelta(hours=tz_offset_hours)
    now_str = f"{now_local.strftime('%Y-%m-%d %H:%M:%S')} (UTC{tz_offset_hours:+})"

    if not corpus:
        return " No documents found in `documents/` folder."

    query_emb = retriever_model.encode(query, convert_to_tensor=True)
    corpus_emb = retriever_model.encode(corpus, convert_to_tensor=True)

    hits = util.semantic_search(query_emb, corpus_emb, top_k=3)[0]
    context_chunks = [corpus[hit["corpus_id"]] for hit in hits]
    context = "\n\n".join(context_chunks)

    if not context:
        return " I couldn't find relevant information in documents."

    return generate_answer_local(context, query, now_str)


def main():
    corpus = load_documents()
    if not corpus:
        print(" No documents loaded. Put .txt or .pdf files in `documents/` folder.")
    else:
        print(f" Loaded {len(corpus)} documents.")

    print("RAG System Ready! Type 'exit' to quit.")

    while True:
        query = input("\nYou: ")
        if query.lower() in ["exit", "quit", "bye"]:
            print(" Goodbye!")
            break
        answer = answer_query(query, corpus, retriever_model, tz_offset_hours=5.5)  # adjust offset if needed
        print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    main()
