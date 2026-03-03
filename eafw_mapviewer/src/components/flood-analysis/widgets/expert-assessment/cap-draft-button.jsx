import React, { useState } from "react";
import PropTypes from "prop-types";
import { createCapDraft } from "@/services/cap";
import Button from "@/components/ui/button";

const CapDraftButton = ({ assessmentId, disabled }) => {
  const [state, setState] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);

  const handleClick = async () => {
    setState("loading");
    try {
      const data = await createCapDraft(assessmentId);
      setResult(data);
      setState("success");
    } catch (err) {
      setResult({ message: err?.response?.data?.detail || err.message || "Failed" });
      setState("error");
    }
  };

  if (state === "success" && result) {
    return (
      <div className="cap-draft-result" style={{ padding: "8px 0" }}>
        <span style={{ color: "#2e7d32", fontWeight: 600, fontSize: 13 }}>
          CAP alert draft created.
        </span>{" "}
        <a
          href={result.edit_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "#1565c0", fontWeight: 600, fontSize: 13 }}
        >
          Edit in CMS Admin &rarr;
        </a>
      </div>
    );
  }

  if (state === "error" && result) {
    return (
      <div className="cap-draft-result" style={{ padding: "8px 0" }}>
        <span style={{ color: "#c62828", fontSize: 13 }}>
          CAP draft failed: {result.message}
        </span>
        <Button
          theme="theme-button-light"
          onClick={() => { setState("idle"); setResult(null); }}
          style={{ marginLeft: 8, fontSize: 12 }}
        >
          Retry
        </Button>
      </div>
    );
  }

  return (
    <Button
      theme="theme-button-light"
      onClick={handleClick}
      disabled={disabled || state === "loading"}
      style={{
        borderColor: "#1565c0",
        color: "#1565c0",
        fontSize: 13,
      }}
    >
      {state === "loading" ? "Creating CAP Draft..." : "Generate CAP Alert Draft"}
    </Button>
  );
};

CapDraftButton.propTypes = {
  assessmentId: PropTypes.number.isRequired,
  disabled: PropTypes.bool,
};

export default CapDraftButton;
