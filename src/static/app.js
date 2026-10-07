document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupSection = document.getElementById("signup-container");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const authButton = document.getElementById("auth-button");
  const teacherStatus = document.getElementById("teacher-status");
  const loginModal = document.getElementById("login-modal");
  const loginForm = document.getElementById("login-form");
  let teacherToken = null;

  function setTeacherSession(username, token) {
    teacherToken = token;
    teacherStatus.textContent = `Teacher: ${username}`;
    authButton.textContent = "Log out";
    authButton.setAttribute("aria-label", "Teacher logout");
    signupSection.classList.remove("hidden");
    fetchActivities();
  }

  function clearTeacherSession() {
    teacherToken = null;
    teacherStatus.textContent = "Public view";
    authButton.textContent = "👤 Teacher login";
    authButton.setAttribute("aria-label", "Teacher login");
    signupSection.classList.add("hidden");
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);
  }

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  authButton.addEventListener("click", async () => {
    if (!teacherToken) {
      loginModal.classList.remove("hidden");
      document.getElementById("teacher-username").focus();
      return;
    }

    try {
      const response = await fetch("/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${teacherToken}` },
      });
      if (!response.ok) {
        showMessage("Unable to log out. Please try again.", "error");
        return;
      }
    } catch (error) {
      showMessage("Unable to log out. Please try again.", "error");
      console.error("Error logging out:", error);
      return;
    }
    clearTeacherSession();
    fetchActivities();
  });

  document.getElementById("cancel-login").addEventListener("click", () => {
    loginModal.classList.add("hidden");
    loginForm.reset();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("teacher-username").value;
    const password = document.getElementById("teacher-password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Unable to log in.", "error");
        return;
      }

      loginModal.classList.add("hidden");
      loginForm.reset();
      setTeacherSession(result.username, result.access_token);
      showMessage("Teacher login successful.", "success");
    } catch (error) {
      showMessage("Unable to log in. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  });

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(activitySelect.options[0]);

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) => `<li>
                      <span class="participant-email">${escapeHtml(email)}</span>
                      ${teacherToken ? `<button class="delete-btn" data-activity="${encodeURIComponent(name)}" data-email="${encodeURIComponent(email)}" aria-label="Unregister ${escapeHtml(email)}">Unregister</button>` : ""}
                    </li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = decodeURIComponent(button.getAttribute("data-activity"));
    const email = decodeURIComponent(button.getAttribute("data-email"));

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email        )}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${teacherToken}` },
        }
      );

      const result = await response.json();

      if (response.status === 401) {
        clearTeacherSession();
        fetchActivities();
      }

      if (response.ok) {
        showMessage(result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email        )}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${teacherToken}` },
        }
      );

      const result = await response.json();

      if (response.status === 401) {
        clearTeacherSession();
        fetchActivities();
      }

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to register the student. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  signupSection.classList.add("hidden");
  fetchActivities();
});
