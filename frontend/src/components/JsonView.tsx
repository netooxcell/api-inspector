import { Fragment } from "react";

function tokenize(json: string) {
  const regex = /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(\.\d+)?([eE][+-]?\d+)?)/g;
  const parts: { text: string; className?: string }[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(json)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ text: json.slice(lastIndex, match.index) });
    }
    const token = match[0];
    let className = "json-number";
    if (/^"/.test(token)) {
      className = /:\s*$/.test(token) ? "json-key" : "json-string";
    } else if (/true|false/.test(token)) {
      className = "json-bool";
    } else if (/null/.test(token)) {
      className = "json-null";
    }
    parts.push({ text: token, className });
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < json.length) {
    parts.push({ text: json.slice(lastIndex) });
  }
  return parts;
}

export default function JsonView({ text }: { text: string }) {
  const parts = tokenize(text);
  return (
    <pre className="code-block">
      {parts.map((p, i) => (
        <Fragment key={i}>
          {p.className ? <span className={p.className}>{p.text}</span> : p.text}
        </Fragment>
      ))}
    </pre>
  );
}
