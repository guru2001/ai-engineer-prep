import { useEffect, useRef, useState } from "react";
import {
  ask,
  deleteDocument,
  getHistory,
  listDocuments,
  uploadDocument,
  type DocumentOut,
  type MessageOut,
} from "./api";

export default function App() {
  const [docs, setDocs] = useState<DocumentOut[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  const activeDoc = docs.find((d) => d.id === activeId) ?? null;

  useEffect(() => {
    listDocuments().then(setDocs).catch((e) => setError(String(e.message)));
  }, []);

  useEffect(() => {
    if (activeId == null) {
      setMessages([]);
      return;
    }
    getHistory(activeId).then(setMessages).catch((e) => setError(String(e.message)));
  }, [activeId]);

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, asking]);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const doc = await uploadDocument(file);
      setDocs((prev) => [doc, ...prev]);
      setActiveId(doc.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function onDelete(id: number) {
    try {
      await deleteDocument(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
      if (activeId === id) setActiveId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onAsk(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || activeId == null || asking) return;
    setError(null);
    setAsking(true);
    setQuestion("");
    const optimistic: MessageOut = {
      id: Date.now(),
      role: "user",
      content: q,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    try {
      const res = await ask(activeId, q);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">◧</span> DocLens
        </div>
        <p className="tagline">Chat with your PDFs — grounded, cited answers.</p>

        <button
          className="upload-btn"
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
        >
          {uploading ? "Uploading…" : "+ Upload PDF"}
        </button>
        <input
          ref={fileInput}
          type="file"
          accept="application/pdf"
          onChange={onUpload}
          hidden
        />

        <div className="doclist">
          {docs.length === 0 && <p className="empty">No documents yet.</p>}
          {docs.map((d) => (
            <div
              key={d.id}
              className={"docitem" + (d.id === activeId ? " active" : "")}
              onClick={() => setActiveId(d.id)}
            >
              <span className="docname" title={d.filename}>
                {d.filename}
              </span>
              <button
                className="del"
                title="Delete"
                onClick={(ev) => {
                  ev.stopPropagation();
                  onDelete(d.id);
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      <main className="chat">
        {activeDoc ? (
          <>
            <header className="chat-head">
              <h1>{activeDoc.filename}</h1>
              <span className="meta">
                {(activeDoc.size_bytes / 1024).toFixed(0)} KB
              </span>
            </header>

            <div className="feed" ref={feedRef}>
              {messages.length === 0 && (
                <div className="hint">
                  Ask anything about this document. Answers cite the exact pages
                  they came from.
                </div>
              )}
              {messages.map((m) => (
                <div key={m.id} className={"msg " + m.role}>
                  <div className="bubble">{m.content}</div>
                  {m.citations.length > 0 && (
                    <div className="citations">
                      {m.citations.map((c, i) => (
                        <div className="cite" key={i}>
                          {c.start_page != null && (
                            <span className="page">
                              {c.end_page == null || c.start_page === c.end_page
                                ? `p. ${c.start_page}`
                                : `pp. ${c.start_page}–${c.end_page}`}
                            </span>
                          )}
                          <span className="quote">“{c.cited_text.trim()}”</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {asking && (
                <div className="msg assistant">
                  <div className="bubble thinking">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              )}
            </div>

            {error && <div className="error">{error}</div>}

            <form className="composer" onSubmit={onAsk}>
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about this PDF…"
                disabled={asking}
              />
              <button type="submit" disabled={asking || !question.trim()}>
                Ask
              </button>
            </form>
          </>
        ) : (
          <div className="placeholder">
            <div className="logo-lg">◧</div>
            <h2>Upload a PDF to get started</h2>
            <p>
              DocLens reads the whole document and answers your questions with
              inline citations to the exact page — no hallucinated sources.
            </p>
            {error && <div className="error">{error}</div>}
          </div>
        )}
      </main>
    </div>
  );
}
