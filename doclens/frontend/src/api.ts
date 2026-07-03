export interface DocumentOut {
  id: number;
  filename: string;
  size_bytes: number;
  created_at: string;
}

export interface Citation {
  cited_text: string;
  start_page: number | null;
  end_page: number | null;
}

export interface MessageOut {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface AnswerOut {
  answer: string;
  citations: Citation[];
}

async function handle(res: Response) {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(detail || `${res.status} ${res.statusText}`);
  }
  return res.status === 204 ? null : res.json();
}

export const listDocuments = (): Promise<DocumentOut[]> =>
  fetch("/api/documents").then(handle);

export const uploadDocument = (file: File): Promise<DocumentOut> => {
  const form = new FormData();
  form.append("file", file);
  return fetch("/api/documents", { method: "POST", body: form }).then(handle);
};

export const deleteDocument = (id: number): Promise<null> =>
  fetch(`/api/documents/${id}`, { method: "DELETE" }).then(handle);

export const getHistory = (id: number): Promise<MessageOut[]> =>
  fetch(`/api/documents/${id}/messages`).then(handle);

export const ask = (id: number, question: string): Promise<AnswerOut> =>
  fetch(`/api/documents/${id}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  }).then(handle);
