export default function KeyValueTable({ data }: { data: Record<string, string> | null | undefined }) {
  const entries = data ? Object.entries(data) : [];
  if (entries.length === 0) {
    return <p className="empty-note">None</p>;
  }
  return (
    <table className="kv-table">
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <td className="kv-key">{key}</td>
            <td className="kv-value">{String(value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
