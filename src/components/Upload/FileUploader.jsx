import { useState } from "react";
import "./FileUploader.css";

export default function FileUploader({ onFileSelect, onTranscriptionComplete, lastResult }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [transcription, setTranscription] = useState("");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  const BACKEND_URL = "http://localhost:8000";
  const SUPPORTED_FORMATS = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"];

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setError("");
    
    if (selectedFile) {
      const ext = "." + selectedFile.name.split(".").pop().toLowerCase();
      if (!SUPPORTED_FORMATS.includes(ext)) {
        setError(`Unsupported format. Supported: ${SUPPORTED_FORMATS.join(", ")}`);
        return;
      }
      setFile(selectedFile);
      onFileSelect?.(selectedFile);
    }
  };

  const handleTranscribe = async () => {
    if (!file) {
      setError("Please select a video file");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("query", query || "Transcribe this video");

    setUploading(true);
    setProgress(0);
    setError("");
    setTranscription("");

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) clearInterval(progressInterval);
          return Math.min(prev + Math.random() * 30, 90);
        });
      }, 500);

      const response = await fetch(`${BACKEND_URL}/query`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Transcription failed");
      }

      const result = await response.json();
      setTranscription(result.transcription || result.response || "");
      onTranscriptionComplete?.(result);
    } catch (err) {
      setError(err.message || "Error transcribing video");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-uploader">
      <h3>📹 Video Upload & Agent Router</h3>

      <p className="agent-hint">
        Use queries like "transcribe this video", "summarize the video", or "what objects do you see?"
      </p>

      <div className="upload-section">
        <label htmlFor="video-input" className="file-label">
          Choose Video File
        </label>
        <input
          id="video-input"
          type="file"
          accept={SUPPORTED_FORMATS.join(",")}
          onChange={handleFileChange}
          disabled={uploading}
        />
        {file && <p className="file-name">✓ Selected: {file.name}</p>}
      </div>

      <div className="query-section">
        <label htmlFor="query-input">Query/Notes (optional):</label>
        <input
          id="query-input"
          type="text"
          placeholder="What would you like to know about this video?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={uploading}
        />
      </div>

      <button
        onClick={handleTranscribe}
        disabled={!file || uploading}
        className="transcribe-btn"
      >
        {uploading ? `Processing... ${Math.round(progress)}%` : "🎬 Transcribe Video"}
      </button>

      {uploading && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }}></div>
        </div>
      )}

      {error && <div className="error-message">❌ {error}</div>}

      {lastResult?.agent && (
        <div className="agent-result">
          <strong>Active agent:</strong> {lastResult.agent}
        </div>
      )}

      {transcription && (
        <div className="transcription-result">
          <h4>📝 Agent Output:</h4>
          <p>{transcription}</p>
        </div>
      )}
    </div>
  );
}