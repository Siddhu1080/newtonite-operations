import WorkItemDetails from "./WorkItemDetails";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  Bell,
  Check,
  ChevronDown,
  ClipboardList,
  Clock3,
  LayoutDashboard,
  Leaf,
  LogOut,
  Menu,
  Plus,
  Search,
  Settings,
  Users,
  X,
  Zap,
} from "lucide-react";
import Auth from "./Auth";
import {
  apiRequest,
  getCurrentUser,
  logout,
  updateWorkItem,
} from "./api";
import "./App.css";

function App() {
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [teams, setTeams] = useState([]);
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);

  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newPriority, setNewPriority] = useState("Medium");
  const [newTeamId, setNewTeamId] = useState("");

  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [updatingId, setUpdatingId] = useState(null);
  const [activePage, setActivePage] = useState("Overview");
  

  async function loadUser() {
    const token = localStorage.getItem("access_token");

    if (!token) {
      setUser(null);
      return;
    }

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setError("");
    } catch (err) {
      logout();
      setUser(null);
      setError(err.message || "Please sign in again.");
    }
  }

  async function loadWorkspaceData() {
    setDataLoading(true);
    setError("");

    try {
      const [workItems, myTeams] = await Promise.all([
        apiRequest("/work-items/?skip=0&limit=100"),
        apiRequest("/teams/"),
      ]);

      setTasks(
        workItems.map((item) => ({
          ...item,
          team:
            myTeams.find((team) => team.id === item.team_id)?.name ||
            `Team ${item.team_id}`,
          assignee: item.assignee_id
            ? `User ${item.assignee_id}`
            : "Unassigned",
        }))
      );

      setTeams(myTeams);

      if (myTeams.length > 0 && !newTeamId) {
        setNewTeamId(String(myTeams[0].id));
      }
    } catch (err) {
      setError(err.message || "Could not load workspace data.");
    } finally {
      setDataLoading(false);
    }
  }

  useEffect(() => {
    loadUser().finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    if (user) {
      loadWorkspaceData();
    }
  }, [user]);

  function handleLogout() {
    logout();
    setUser(null);
    setTasks([]);
    setTeams([]);
    setError("");
    setSuccess("");
    setMobileMenu(false);
    setActivePage("Overview");
  }

  const visibleTasks = tasks.filter((task) => {
    const matchesFilter = filter === "All" || task.status === filter;

    const matchesSearch =
      task.title.toLowerCase().includes(search.toLowerCase()) ||
      task.team.toLowerCase().includes(search.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  async function handleStatusChange(task, newStatus) {
    if (task.status === newStatus) return;

    setError("");
    setSuccess("");
    setUpdatingId(task.id);

    try {
      await updateWorkItem(task.id, {
        status: newStatus,
        version: task.version,
      });

      setSuccess(`"${task.title}" status updated to ${newStatus}.`);

      await loadWorkspaceData();
    } catch (err) {
      setError(err.message || "Could not update the work item status.");
    } finally {
      setUpdatingId(null);
    }
  }

  async function createTask(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!newTitle.trim()) {
      setError("Please enter a work item title.");
      return;
    }

    if (!newTeamId) {
      setError("Please select a team you belong to.");
      return;
    }

    try {
      await apiRequest("/work-items/", {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify({
          title: newTitle.trim(),
          description: newDescription.trim() || null,
          team_id: Number(newTeamId),
          assignee_id: null,
          priority: newPriority,
        }),
      });

      setNewTitle("");
      setNewDescription("");
      setNewPriority("Medium");
      setShowCreate(false);
      setSuccess("Work item created successfully.");

      await loadWorkspaceData();
    } catch (err) {
      setError(err.message || "Could not create the work item.");
    }
  }

  function navigateTo(page) {
    setActivePage(page);
    setMobileMenu(false);
    setError("");
    setSuccess("");
  }

  if (authLoading) {
    return (
      <div className="auth-loading">
        <div className="auth-loading-logo">
          <Leaf size={24} />
        </div>
        <p>Loading your workspace...</p>
      </div>
    );
  }

  if (!user) {
    return <Auth onLogin={loadUser} />;
  }

  const initials = user.name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <Zap size={21} fill="currentColor" />
          </div>

          <div>
            <div className="brand-name">newtonite</div>
            <div className="brand-subtitle">OPERATIONS</div>
          </div>

          <button
            className="icon-button mobile-close"
            onClick={() => setMobileMenu(false)}
            aria-label="Close navigation"
          >
            <X size={19} />
          </button>
        </div>

        <div className="workspace-label">WORKSPACE</div>

        <nav className="navigation">
          <button
            className={`nav-item ${
              activePage === "Overview" ? "active" : ""
            }`}
            onClick={() => navigateTo("Overview")}
          >
            <LayoutDashboard size={18} />
            <span>Overview</span>
          </button>

          <button
            className={`nav-item ${
              activePage === "Work items" ? "active" : ""
            }`}
            onClick={() => navigateTo("Work items")}
          >
            <ClipboardList size={18} />
            <span>Work items</span>
            <span className="nav-count">{tasks.length}</span>
          </button>

          <button
            className={`nav-item ${
              activePage === "Teams" ? "active" : ""
            }`}
            onClick={() => navigateTo("Teams")}
          >
            <Users size={18} />
            <span>Teams</span>
          </button>

          <button
            className={`nav-item ${
              activePage === "Activity" ? "active" : ""
            }`}
            onClick={() => navigateTo("Activity")}
          >
            <Activity size={18} />
            <span>Activity</span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="workspace-card">
            <div className="workspace-avatar">N</div>
            <div className="workspace-info">
              <strong>Newtonite</strong>
              <span>Operations workspace</span>
            </div>
            <ChevronDown size={15} />
          </div>

          <button className="nav-item" onClick={() => navigateTo("Settings")}>
            <Settings size={18} />
            <span>Settings</span>
          </button>

          <button
            className="nav-item logout-button"
            onClick={handleLogout}
          >
            <LogOut size={18} />
            <span>Sign out</span>
          </button>

          <div className="sidebar-footer">Built for better teamwork.</div>
        </div>
      </aside>

      {mobileMenu && (
        <button
          className="mobile-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileMenu(false)}
        />
      )}

      <main className="main-area">
        <header className="topbar">
          <button
            className="icon-button mobile-menu-button"
            onClick={() => setMobileMenu(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>

          <div className="breadcrumb">
            Workspace <span>/</span> <strong>{activePage}</strong>
          </div>

          <div className="topbar-right">
            <button
              className="icon-button notification-button"
              aria-label="Notifications"
            >
              <Bell size={19} />
            </button>

            <div className="topbar-divider" />

            <div className="profile">
              <div className="profile-avatar">{initials}</div>
              <div className="profile-text">
                <strong>{user.name}</strong>
                <span>{user.email}</span>
              </div>
              <ChevronDown size={15} />
            </div>
          </div>
        </header>

        <div className="page-content">
          {error && (
            <div className="auth-session-notice" role="alert">
              {error}
            </div>
          )}

          {success && (
            <div className="auth-session-notice" role="status">
              {success}
            </div>
          )}

          {/* OVERVIEW PAGE */}
          {activePage === "Overview" && (
            <>
              <section className="welcome-row">
                <div>
                  <div className="eyebrow">
                    <span /> YOUR WORKSPACE
                  </div>
                  <h1>Good to see you, {user.name.split(" ")[0]}.</h1>
                  <p>
                    Here's what's happening across your workspace today.
                  </p>
                </div>

                <button
                  className="primary-button"
                  onClick={() => setShowCreate(true)}
                >
                  <Plus size={18} />
                  Create work item
                </button>
              </section>

              <section className="stats-grid">
                <StatCard
                  label="Total work items"
                  value={tasks.length}
                  icon={<ClipboardList size={19} />}
                  tone="orange"
                  detail="Across your teams"
                />
                <StatCard
                  label="In progress"
                  value={
                    tasks.filter((task) => task.status === "In Progress")
                      .length
                  }
                  icon={<Clock3 size={19} />}
                  tone="amber"
                  detail="Currently being worked on"
                />
                <StatCard
                  label="Completed"
                  value={
                    tasks.filter((task) => task.status === "Completed")
                      .length
                  }
                  icon={<Check size={19} />}
                  tone="green"
                  detail="Finished work items"
                />
                <StatCard
                  label="Open"
                  value={tasks.filter((task) => task.status === "Open").length}
                  icon={<ArrowRight size={19} />}
                  tone="slate"
                  detail="Waiting to get started"
                />
              </section>

              <WorkItemsSection
                tasks={visibleTasks}
                totalTasks={tasks.length}
                dataLoading={dataLoading}
                search={search}
                setSearch={setSearch}
                filter={filter}
                setFilter={setFilter}
                onCreate={() => setShowCreate(true)}
                onStatusChange={handleStatusChange}
                setSelectedTask={setSelectedTask}
                updatingId={updatingId}
              />

              <section className="bottom-grid">
                <div className="info-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Quick overview</h3>
                      <p>A snapshot of your current work.</p>
                    </div>
                    <div className="panel-icon">
                      <Activity size={18} />
                    </div>
                  </div>

                  <div className="overview-line">
                    <span>Open work</span>
                    <strong>
                      {tasks.filter((task) => task.status === "Open").length}
                    </strong>
                  </div>

                  <div className="overview-line">
                    <span>Being worked on</span>
                    <strong>
                      {
                        tasks.filter(
                          (task) => task.status === "In Progress"
                        ).length
                      }
                    </strong>
                  </div>

                  <div className="overview-line">
                    <span>Finished</span>
                    <strong>
                      {
                        tasks.filter((task) => task.status === "Completed")
                          .length
                      }
                    </strong>
                  </div>
                </div>

                <div className="info-panel activity-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Activity</h3>
                      <p>Recent workspace updates.</p>
                    </div>
                    <div className="panel-icon">
                      <Zap size={18} />
                    </div>
                  </div>

                  <div className="activity-item">
                    <div className="activity-avatar">{initials}</div>
                    <div>
                      <p>
                        <strong>Welcome, {user.name.split(" ")[0]}</strong>
                      </p>
                      <span>You're signed in to Newtonite Operations.</span>
                    </div>
                  </div>

                  <div className="activity-item">
                    <div className="activity-avatar activity-avatar-orange">
                      N
                    </div>
                    <div>
                      <p>
                        <strong>Work items connected</strong>
                      </p>
                      <span>
                        The list above is loaded from your backend API.
                      </span>
                    </div>
                  </div>
                </div>
              </section>
            </>
          )}

          {/* WORK ITEMS PAGE */}
          {activePage === "Work items" && (
            <>
              <section className="welcome-row">
                <div>
                  <div className="eyebrow">
                    <span /> YOUR WORKSPACE
                  </div>
                  <h1>Work items</h1>
                  <p>Manage tasks across your teams.</p>
                </div>

                <button
                  className="primary-button"
                  onClick={() => setShowCreate(true)}
                >
                  <Plus size={18} />
                  Create work item
                </button>
              </section>

              <WorkItemsSection
                tasks={visibleTasks}
                totalTasks={tasks.length}
                dataLoading={dataLoading}
                search={search}
                setSearch={setSearch}
                filter={filter}
                setFilter={setFilter}
                onCreate={() => setShowCreate(true)}
                onStatusChange={handleStatusChange}
                updatingId={updatingId}
              />
            </>
          )}

          {/* TEAMS PAGE */}
          {activePage === "Teams" && (
            <>
              <section className="welcome-row">
                <div>
                  <div className="eyebrow">
                    <span /> YOUR WORKSPACE
                  </div>
                  <h1>Teams</h1>
                  <p>View your teams and the people working with you.</p>
                </div>
              </section>

              {dataLoading && <p role="status">Loading teams...</p>}

              {!dataLoading && teams.length === 0 && (
                <div className="info-panel">
                  <h3>No teams found</h3>
                  <p>You don't currently belong to any teams.</p>
                </div>
              )}

              {teams.length > 0 && (
                <div className="teams-grid">
                  {teams.map((team) => (
                    <TeamCard key={team.id} team={team} />
                  ))}
                </div>
              )}
            </>
          )}

          {/* ACTIVITY PAGE */}
          {activePage === "Activity" && (
            <>
              <section className="welcome-row">
                <div>
                  <div className="eyebrow">
                    <span /> YOUR WORKSPACE
                  </div>
                  <h1>Activity</h1>
                  <p>Workspace activity overview.</p>
                </div>
              </section>

              <div className="info-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Recent activity</h3>
                    <p>Basic workspace information.</p>
                  </div>
                  <div className="panel-icon">
                    <Activity size={18} />
                  </div>
                </div>

                <div className="activity-item">
                  <div className="activity-avatar">{initials}</div>
                  <div>
                    <p>
                      <strong>{user.name} signed in</strong>
                    </p>
                    <span>You're signed in to Newtonite Operations.</span>
                  </div>
                </div>

                <div className="activity-item">
                  <div className="activity-avatar activity-avatar-orange">
                    N
                  </div>
                  <div>
                    <p>
                      <strong>Work items loaded</strong>
                    </p>
                    <span>{tasks.length} work items are available.</span>
                  </div>
                </div>

                <p>
                  Note: this page currently shows a basic summary, not the
                  backend activity log.
                </p>
              </div>
            </>
          )}

          {/* SETTINGS PAGE */}
          {activePage === "Settings" && (
            <>
              <section className="welcome-row">
                <div>
                  <div className="eyebrow">
                    <span /> YOUR WORKSPACE
                  </div>
                  <h1>Settings</h1>
                  <p>Your account information.</p>
                </div>
              </section>

              <div className="info-panel">
                <h3>Account details</h3>
                <div className="overview-line">
                  <span>Name</span>
                  <strong>{user.name}</strong>
                </div>
                <div className="overview-line">
                  <span>Email</span>
                  <strong>{user.email}</strong>
                </div>
                <div className="overview-line">
                  <span>Account status</span>
                  <strong>{user.is_active ? "Active" : "Inactive"}</strong>
                </div>
              </div>
            </>
          )}

          <footer className="page-footer">
            <span>Newtonite Operations</span>
            <span>Simple tools. Better teamwork.</span>
          </footer>
        </div>
      </main>

      {/* CREATE WORK ITEM MODAL */}
      {selectedTask && (
  <WorkItemDetails
    task={selectedTask}
    onClose={() => setSelectedTask(null)}
  />
)}
      {showCreate && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setShowCreate(false);
            }
          }}
        >
          <form className="create-modal" onSubmit={createTask}>
            <div className="modal-heading">
              <div>
                <div className="eyebrow">
                  <span /> NEW WORK ITEM
                </div>
                <h2>Create a work item</h2>
                <p>Add a task to one of your teams.</p>
              </div>

              <button
                type="button"
                className="icon-button"
                onClick={() => setShowCreate(false)}
                aria-label="Close modal"
              >
                <X size={19} />
              </button>
            </div>

            <label htmlFor="task-title">Title</label>
            <input
              id="task-title"
              autoFocus
              required
              maxLength={200}
              value={newTitle}
              onChange={(event) => setNewTitle(event.target.value)}
              placeholder="e.g. Review API documentation"
            />

            <label htmlFor="task-description">Description</label>
            <textarea
              id="task-description"
              value={newDescription}
              onChange={(event) => setNewDescription(event.target.value)}
              placeholder="Optional description"
              rows={3}
            />

            <label htmlFor="task-team">Team</label>
            <select
              id="task-team"
              value={newTeamId}
              onChange={(event) => setNewTeamId(event.target.value)}
              required
            >
              <option value="">Select a team</option>
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>

            {teams.length === 0 && (
              <p role="status">
                You don't belong to any teams. Create a team before adding
                work items.
              </p>
            )}

            <label htmlFor="task-priority">Priority</label>
            <select
              id="task-priority"
              value={newPriority}
              onChange={(event) => setNewPriority(event.target.value)}
            >
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
              <option>Urgent</option>
            </select>

            <div className="modal-note">
              <ClipboardList size={16} />
              Work items are saved through the API.
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setShowCreate(false)}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="primary-button"
                disabled={dataLoading || teams.length === 0}
              >
                <Plus size={16} />
                Create item
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function WorkItemsSection({
  tasks,
  totalTasks,
  dataLoading,
  search,
  setSearch,
  filter,
  setFilter,
  onCreate,
  onStatusChange,
   setSelectedTask,
  updatingId,
}) {
  return (
    <section className="work-section">
      <div className="section-heading">
        <div>
          <h2>Work items</h2>
          <p>Your team's tasks, all in one place.</p>
        </div>

        <button className="secondary-button" onClick={onCreate}>
          <Plus size={16} />
          New item
        </button>
      </div>

      <div className="toolbar">
        <div className="search-box">
          <Search size={17} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search work items..."
            aria-label="Search work items"
          />

          {search && (
            <button
              className="clear-search"
              onClick={() => setSearch("")}
              aria-label="Clear search"
            >
              <X size={15} />
            </button>
          )}
        </div>

        <div className="filter-control">
          <span>Status:</span>
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          >
            <option value="All">All statuses</option>
            <option value="Open">Open</option>
            <option value="In Progress">In Progress</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
          </select>
          <ChevronDown size={14} />
        </div>
      </div>

      {dataLoading && <p role="status">Loading work items...</p>}

      <div className="task-table-wrap">
        <table className="task-table">
          <thead>
            <tr>
              <th>Work item</th>
              <th>Team</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Assignee</th>
              <th aria-label="Actions" />
            </tr>
          </thead>

          <tbody>
            {tasks.map((task) => (
              <tr key={task.id}>
                <td>
                  <div className="task-title-cell">
                    <span
                      className={`task-check ${
                        task.status === "Completed" ? "task-check-done" : ""
                      }`}
                    >
                      {task.status === "Completed" && <Check size={12} />}
                    </span>
                    <button
  type="button"
  className="task-title task-title-button"
  onClick={() => setSelectedTask(task)}
>
  {task.title}
</button>
                  </div>
                </td>

                <td>
                  <span className="team-name">{task.team}</span>
                </td>

                <td>
                  <StatusBadge status={task.status} />
                </td>

                <td>
                  <PriorityBadge priority={task.priority} />
                </td>

                <td>
                  <div className="assignee">
                    <span className="assignee-avatar">
                      {task.assignee === "Unassigned" ? "—" : task.assignee}
                    </span>
                  </div>
                </td>

                <td>
                  <select
                    className="status-select"
                    aria-label={`Change status for ${task.title}`}
                    value={task.status}
                    disabled={updatingId === task.id}
                    onChange={(event) =>
                      onStatusChange(task, event.target.value)
                    }
                  >
                    <option value="Open">Open</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Completed">Completed</option>
                    <option value="Cancelled">Cancelled</option>
                  </select>
                </td>
              </tr>
            ))}

            {!dataLoading && tasks.length === 0 && (
              <tr>
                <td colSpan="6">
                  <div className="empty-state">
                    <ClipboardList size={26} />
                    <strong>No work items found</strong>
                    <span>
                      Try a different search or create a new item.
                    </span>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span>
          Showing <strong>{tasks.length}</strong> of{" "}
          <strong>{totalTasks}</strong> work items
        </span>
        <span className="footer-note">
          <span /> Live API data
        </span>
      </div>
    </section>
  );
}

function TeamCard({ team }) {
  const [members, setMembers] = useState([]);
  const [expanded, setExpanded] = useState(false);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [memberError, setMemberError] = useState("");

  async function toggleMembers() {
    if (expanded) {
      setExpanded(false);
      return;
    }

    setExpanded(true);

    if (members.length > 0) return;

    setLoadingMembers(true);
    setMemberError("");

    try {
      const data = await apiRequest(`/teams/${team.id}/members`);
      setMembers(Array.isArray(data) ? data : []);
    } catch (err) {
      setMemberError(err.message || "Could not load team members.");
    } finally {
      setLoadingMembers(false);
    }
  }

  return (
    <div className="info-panel team-card">
      <div className="team-card-heading">
        <div className="workspace-avatar">
          {team.name?.charAt(0).toUpperCase() || "T"}
        </div>

        <div>
          <h3>{team.name}</h3>
          <p>Team ID: {team.id}</p>
        </div>
      </div>

      <button
        className="secondary-button"
        type="button"
        onClick={toggleMembers}
      >
        <Users size={16} />
        {expanded ? "Hide members" : "View members"}
        <ChevronDown size={15} />
      </button>

      {expanded && (
        <div className="team-members">
          {loadingMembers && <p>Loading members...</p>}

          {memberError && <p className="team-error">{memberError}</p>}

          {!loadingMembers && !memberError && members.length === 0 && (
            <p>No members returned for this team.</p>
          )}

          {!loadingMembers &&
            !memberError &&
            members.map((member, index) => {
              const memberName =
                member.name ||
                member.user?.name ||
                `Member ${index + 1}`;

              const memberEmail =
                member.email || member.user?.email || "";

              const memberRole =
                member.role || member.team_role || "Member";

              const memberId =
                member.user_id ??
                member.user?.id ??
                member.id ??
                index;

              return (
                <div className="team-member" key={memberId}>
                  <div className="profile-avatar">
                    {memberName.charAt(0).toUpperCase()}
                  </div>

                  <div className="team-member-info">
                    <strong>{memberName}</strong>
                    <span>{memberEmail || "No email available"}</span>
                  </div>

                  <span className="status-badge status-open">
                    {memberRole}
                  </span>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, tone, detail }) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span className={`stat-icon ${tone}`}>{icon}</span>
        <span className="stat-detail">{detail}</span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const className = status.toLowerCase().replace(" ", "-");

  return (
    <span className={`status-badge status-${className}`}>
      {status}
    </span>
  );
}

function PriorityBadge({ priority }) {
  return (
    <span className={`priority-badge priority-${priority.toLowerCase()}`}>
      {priority}
    </span>
  );
}

export default App;