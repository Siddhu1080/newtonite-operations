import { useEffect, useState } from "react";
import {
  Activity,
  CalendarDays,
  MessageSquare,
  Send,
  X,
  RefreshCw,
} from "lucide-react";
import { apiRequest } from "./api";
import "./WorkItemDetails.css";

function WorkItemDetails({ task, onClose }) {
  const [comments, setComments] = useState([]);
  const [activities, setActivities] = useState([]);
  const [commentText, setCommentText] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function loadDetails() {
    setLoading(true);
    setError("");

    try {
      const results = await Promise.allSettled([
        apiRequest(`/work-items/${task.id}/comments/`),
        apiRequest(`/work-items/${task.id}/activities/`),
      ]);

      const commentsResult = results[0];
      const activitiesResult = results[1];

      if (commentsResult.status === "fulfilled") {
        setComments(
          Array.isArray(commentsResult.value) ? commentsResult.value : []
        );
      } else {
        setComments([]);
      }

      if (activitiesResult.status === "fulfilled") {
        setActivities(
          Array.isArray(activitiesResult.value)
            ? activitiesResult.value
            : []
        );
      } else {
        setActivities([]);
      }

      if (
        commentsResult.status === "rejected" &&
        activitiesResult.status === "rejected"
      ) {
        setError(
          "Could not load comments or activity. Please check your connection."
        );
      } else if (commentsResult.status === "rejected") {
        setError("Comments could not be loaded.");
      } else if (activitiesResult.status === "rejected") {
        setError("Activity logs could not be loaded.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDetails();
  }, [task.id]);

  async function handleAddComment(event) {
    event.preventDefault();

    const body = commentText.trim();

    if (!body) {
      setError("Please enter a comment.");
      return;
    }

    setSending(true);
    setError("");
    setSuccess("");

    try {
      await apiRequest(`/work-items/${task.id}/comments/`, {
        method: "POST",
        body: JSON.stringify({ body }),
      });

      setCommentText("");
      setSuccess("Comment added successfully.");

      // Reload both comments and activity after adding the comment.
      await loadDetails();
    } catch (err) {
      setError(err.message || "Could not add the comment.");
    } finally {
      setSending(false);
    }
  }

  function formatDate(value) {
    if (!value) return "Date unavailable";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return value;

    return date.toLocaleString();
  }

  function formatAction(action) {
    if (!action) return "Activity recorded";

    return action
      .replaceAll(".", " ")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  return (
    <div className="details-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section
        className="details-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-title"
      >
        <header className="details-header">
          <div>
            <span className="details-eyebrow">WORK ITEM DETAILS</span>
            <h2 id="details-title">{task.title}</h2>
            <p>{task.description || "No description provided."}</p>
          </div>

          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close work item details"
          >
            <X size={20} />
          </button>
        </header>

        <div className="details-meta">
          <div>
            <span>Status</span>
            <strong>{task.status}</strong>
          </div>
          <div>
            <span>Priority</span>
            <strong>{task.priority}</strong>
          </div>
          <div>
            <span>Team</span>
            <strong>{task.team}</strong>
          </div>
          <div>
            <span>Work item ID</span>
            <strong>#{task.id}</strong>
          </div>
        </div>

        {error && (
          <div className="details-message details-error" role="alert">
            {error}
          </div>
        )}

        {success && (
          <div className="details-message details-success" role="status">
            {success}
          </div>
        )}

        <div className="details-content">
          <section className="details-section">
            <div className="details-section-heading">
              <MessageSquare size={18} />
              <div>
                <h3>Comments</h3>
                <p>{comments.length} comments</p>
              </div>
            </div>

            <form className="comment-form" onSubmit={handleAddComment}>
              <textarea
                value={commentText}
                onChange={(event) => setCommentText(event.target.value)}
                placeholder="Write a comment..."
                rows={3}
                maxLength={2000}
                aria-label="Write a comment"
              />

              <div className="comment-form-footer">
                <span>Keep your team updated.</span>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={sending || !commentText.trim()}
                >
                  <Send size={15} />
                  {sending ? "Sending..." : "Add comment"}
                </button>
              </div>
            </form>

            {loading ? (
              <p className="details-loading">Loading comments...</p>
            ) : comments.length === 0 ? (
              <div className="details-empty">
                <MessageSquare size={22} />
                <strong>No comments yet</strong>
                <span>Be the first to leave a comment.</span>
              </div>
            ) : (
              <div className="comments-list">
                {comments.map((comment) => (
                  <article className="comment-item" key={comment.id}>
                    <div className="comment-avatar">
                      {(comment.user_name || `U${comment.user_id || ""}`)
                        .charAt(0)
                        .toUpperCase()}
                    </div>

                    <div className="comment-main">
                      <div className="comment-topline">
                        <strong>
                          {comment.user_name ||
                            `User ${comment.user_id ?? ""}`}
                        </strong>
                        <span>{formatDate(comment.created_at)}</span>
                      </div>
                      <p>{comment.body}</p>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="details-section">
            <div className="details-section-heading">
              <Activity size={18} />
              <div>
                <h3>Activity history</h3>
                <p>Events recorded by the backend</p>
              </div>

              <button
                type="button"
                className="details-refresh"
                onClick={loadDetails}
                disabled={loading}
                aria-label="Refresh details"
              >
                <RefreshCw size={15} />
              </button>
            </div>

            {loading ? (
              <p className="details-loading">Loading activity...</p>
            ) : activities.length === 0 ? (
              <div className="details-empty">
                <CalendarDays size={22} />
                <strong>No activity found</strong>
                <span>No events were returned for this work item.</span>
              </div>
            ) : (
              <div className="activity-history">
                {activities.map((activity) => (
                  <article className="history-item" key={activity.id}>
                    <span className="history-dot" />

                    <div className="history-main">
                      <strong>{formatAction(activity.action)}</strong>
                      <span>
                        Actor: {activity.actor_id ?? "Unknown"}
                      </span>

                      {activity.new_value && (
                        <details className="activity-values">
                          <summary>View event details</summary>
                          <pre>{String(activity.new_value)}</pre>
                        </details>
                      )}

                      <time>{formatDate(activity.created_at)}</time>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>

        <footer className="details-footer">
          <span>Newtonite Operations</span>
          <button
            type="button"
            className="secondary-button"
            onClick={onClose}
          >
            Close
          </button>
        </footer>
      </section>
    </div>
  );
}

export default WorkItemDetails;