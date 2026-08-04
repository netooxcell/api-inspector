import type { CapturedRequest } from "../types";
import { tryFormatBody } from "../utils";
import KeyValueTable from "./KeyValueTable";
import JsonView from "./JsonView";

export default function RequestTab({ request }: { request: CapturedRequest }) {
  const formattedBody = tryFormatBody(request.req_body);
  const hasParams = request.req_params && Object.keys(request.req_params).length > 0;

  return (
    <div>
      <div className="section">
        <div className="section-title">Method &amp; URL</div>
        <div className="detail-url">
          {request.method} {request.target_url}
        </div>
      </div>

      <div className="section">
        <div className="section-title">Headers</div>
        <KeyValueTable data={request.req_headers} />
      </div>

      {hasParams && (
        <div className="section">
          <div className="section-title">Query Params</div>
          <KeyValueTable data={request.req_params} />
        </div>
      )}

      <div className="section">
        <div className="section-title">Body</div>
        {formattedBody ? <JsonView text={formattedBody} /> : <p className="empty-note">No body</p>}
      </div>
    </div>
  );
}
