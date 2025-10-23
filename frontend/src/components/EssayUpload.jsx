import React, { useState } from "react";
import Navbar from "./Navbar";
import api from "../services/api";
import styles from "../styles/EssayUpload.module.css";

export default function EssayUpload({ onCancel, onUpload, user }) {
  const [file, setFile] = useState(null);
  const [caption, setCaption] = useState("");
  const [visibility, setVisibility] = useState("public");
  const [evaluationData, setEvaluationData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleEvaluate() {
    if (!file) {
      setError("Please select a file first");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post("/api/upload-essay", formData, {
        headers: {
          "Content-Type": "form-data",
        },
      });

      const data = response.data;
      
      if (data.success) {
        setEvaluationData(data);
        console.log("Evaluation data:", data);
      } else {
        console.log("Evaluation data:", data);
        setError(data.error || "Evaluation failed");
      }
      
    } catch (err) {
      console.error("Evaluation error:", err);
      setError(err.response?.data?.error || "Failed to evaluate essay. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit() {
    const newEssay = {
      id: Date.now().toString(),
      author: user.username,
      authorId: user.id,
      caption,
      content: evaluationData?.text_preview || "Essay content...",
      likes: 0,
      comments: 0,
      visibility,
      evaluationData,
    };
    onUpload(newEssay);
  }

  return (
    <>
      <Navbar user={user} />
      <div className={styles.centeredOuter}>
        <div className={styles.card}>
          <h3>Upload Essay</h3>
          
          <input
            type="text"
            placeholder="Essay caption"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            className={styles.input}
          />
          
          <input
            type="file"
            accept=".txt,.docx"
            onChange={(e) => setFile(e.target.files[0])}
            className={styles.fileInput}
          />
          
          {error && <div className={styles.error}>{error}</div>}
          
          <button
            className={styles.button}
            onClick={handleEvaluate}
            disabled={!file || loading}
          >
            {loading ? "Evaluating..." : "Run NLP Evaluation"}
          </button>
          
          {/* Evaluation Results Display */}
          {evaluationData && (
            <div className={styles.resultsContainer}>
              {/* Overall Score */}
              <div className={styles.scoreSection}>
                <h4>Overall Score</h4>
                <div className={styles.scoreCircle}>
                  <span className={styles.scoreValue}>{evaluationData.score}</span>
                  <span className={styles.scoreMax}>/100</span>
                </div>
              </div>

              {/* Grammar Analysis */}
              <div className={styles.section}>
                <h4>📝 Grammar Analysis</h4>
                <div className={styles.stat}>
                  <span className={styles.label}>Total Errors:</span>
                  <span className={styles.value}>{evaluationData.grammar.total_errors}</span>
                </div>
                {evaluationData.grammar.errors.length > 0 && (
                  <div className={styles.errorList}>
                    <p className={styles.errorTitle}>Top Issues:</p>
                    {evaluationData.grammar.errors.slice(0, 3).map((err, idx) => (
                      <div key={idx} className={styles.errorItem}>
                        <p className={styles.errorMsg}>• {err.message}</p>
                        {err.replacements.length > 0 && (
                          <p className={styles.suggestion}>
                            Suggestion: {err.replacements[0]}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Linguistic Stats */}
              <div className={styles.section}>
                <h4>📊 Linguistic Statistics</h4>
                <div className={styles.statsGrid}>
                  <div className={styles.stat}>
                    <span className={styles.label}>Word Count:</span>
                    <span className={styles.value}>{evaluationData.word_count}</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.label}>Sentences:</span>
                    <span className={styles.value}>{evaluationData.linguistics.num_sentences}</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.label}>Avg Sentence Length:</span>
                    <span className={styles.value}>{evaluationData.linguistics.avg_sentence_length} words</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.label}>Named Entities:</span>
                    <span className={styles.value}>{evaluationData.linguistics.num_entities}</span>
                  </div>
                </div>
              </div>

              {/* AI Detection */}
              <div className={styles.section}>
                <h4>🤖 AI Content Detection</h4>
                <div className={styles.aiDetection}>
                  <div className={styles.stat}>
                    <span className={styles.label}>Classification:</span>
                    <span className={`${styles.value} ${styles.aiLabel}`}>
                      {evaluationData.ai_detection.label}
                    </span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.label}>Confidence:</span>
                    <span className={styles.value}>
                      {(evaluationData.ai_detection.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Text Preview */}
              <div className={styles.section}>
                <h4>📄 Text Preview</h4>
                <p className={styles.textPreview}>{evaluationData.text_preview}...</p>
              </div>
            </div>
          )}
          
          {/* Visibility Options */}
          <div className={styles.radioGroup}>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                checked={visibility === "public"}
                onChange={() => setVisibility("public")}
              />
              Public
            </label>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                checked={visibility === "friends"}
                onChange={() => setVisibility("friends")}
              />
              Friends
            </label>
          </div>
          
          <button
            className={styles.button}
            onClick={handleSubmit}
            disabled={!evaluationData || !caption}
          >
            Upload to Feed
          </button>
          <button className={styles.cancelBtn} onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </>
  );
}
