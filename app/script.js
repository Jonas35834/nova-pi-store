const API = "/api";


// ============================================================
// API
// ============================================================

async function api(
    endpoint,
    options = {}
) {

    const response = await fetch(
        API + endpoint,
        options
    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(
            data.error ||
            "API-Fehler"
        );
    }

    return data;
}


// ============================================================
// SERVER STATUS
// ============================================================

async function loadSystem() {

    const status =
        document.getElementById(
            "serverStatus"
        );

    try {

        const data =
            await api("/system");

        status.textContent =
            "● Online";

        status.style.background =
            "#dff7e5";

        document.getElementById(
            "agentCount"
        ).textContent =
            data.agents;

        document.getElementById(
            "taskCount"
        ).textContent =
            data.tasks;

    } catch (error) {

        status.textContent =
            "● Offline";

        status.style.background =
            "#ffe0e0";

        console.error(error);
    }
}


// ============================================================
// AGENTS
// ============================================================

async function loadAgents() {

    const container =
        document.getElementById(
            "agents"
        );

    container.innerHTML =
        "<div class='empty'>Laden...</div>";

    try {

        const data =
            await api("/agents");

        const agents =
            data.agents;

        document.getElementById(
            "agentCount"
        ).textContent =
            agents.length;

        if (agents.length === 0) {

            container.innerHTML =
                "<div class='empty'>Keine Raspberry Pis verbunden.</div>";

            return;
        }

        container.innerHTML =
            agents.map(agent => {

                return `
                    <div class="agent">

                        <h3>
                            🖥️
                            ${escapeHtml(
                                agent.hostname ||
                                "Raspberry Pi"
                            )}
                        </h3>

                        <div class="agent-info">

                            <div>
                                ID:
                                ${escapeHtml(
                                    agent.agent_id
                                )}
                            </div>

                            <div>
                                OS:
                                ${escapeHtml(
                                    agent.os ||
                                    "unbekannt"
                                )}
                            </div>

                            <div>
                                Architektur:
                                ${escapeHtml(
                                    agent.architecture ||
                                    "unbekannt"
                                )}
                            </div>

                            <div>
                                Status:
                                ${escapeHtml(
                                    agent.status ||
                                    "unbekannt"
                                )}
                            </div>

                            <div>
                                Zuletzt gesehen:
                                ${escapeHtml(
                                    agent.last_seen ||
                                    "-"
                                )}
                            </div>

                        </div>

                    </div>
                `;

            }).join("");

    } catch (error) {

        container.innerHTML =
            `
            <div class="empty">
                Fehler:
                ${escapeHtml(
                    error.message
                )}
            </div>
            `;

    }
}


// ============================================================
// STORE
// ============================================================

async function loadStore() {

    const container =
        document.getElementById(
            "apps"
        );

    container.innerHTML =
        "<div class='empty'>Laden...</div>";

    try {

        const data =
            await api("/store");

        const apps =
            data.apps;

        if (!apps.length) {

            container.innerHTML =
                `
                <div class="empty">
                    Keine Apps gefunden.
                    <br>
                    Füge später eine
                    <code>apps.json</code>
                    hinzu.
                </div>
                `;

            return;
        }

        container.innerHTML =
            apps.map(app => {

                const name =
                    app.name ||
                    app.package ||
                    "Unbekannte App";

                const description =
                    app.description ||
                    "Keine Beschreibung.";

                const packageName =
                    app.package ||
                    app.name;

                return `
                    <div class="app">

                        <h3>
                            📦
                            ${escapeHtml(name)}
                        </h3>

                        <div class="app-description">
                            ${escapeHtml(
                                description
                            )}
                        </div>

                        <div>
                            <small>
                                Paket:
                                ${escapeHtml(
                                    packageName
                                )}
                            </small>
                        </div>

                        <div class="app-actions">

                            <button
                                class="install"
                                onclick="installApp(
                                    '${escapeJs(packageName)}'
                                )"
                            >
                                Installieren
                            </button>

                            <button
                                class="remove"
                                onclick="removeApp(
                                    '${escapeJs(packageName)}'
                                )"
                            >
                                Deinstallieren
                            </button>

                        </div>

                    </div>
                `;

            }).join("");

    } catch (error) {

        container.innerHTML =
            `
            <div class="empty">
                Fehler:
                ${escapeHtml(
                    error.message
                )}
            </div>
            `;

    }
}


// ============================================================
// INSTALL
// ============================================================

async function installApp(
    packageName
) {

    const agentId =
        await chooseAgent();

    if (!agentId) {
        return;
    }

    try {

        const data =
            await api(
                "/tasks",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        agent_id:
                            agentId,

                        action:
                            "install",

                        package:
                            packageName
                    })
                }
            );

        alert(
            "Installation wurde gestartet."
        );

        await loadTasks();

    } catch (error) {

        alert(
            "Fehler: " +
            error.message
        );
    }
}


// ============================================================
// REMOVE
// ============================================================

async function removeApp(
    packageName
) {

    const confirmed =
        confirm(
            `Möchtest du ${packageName} wirklich deinstallieren?`
        );

    if (!confirmed) {
        return;
    }

    const agentId =
        await chooseAgent();

    if (!agentId) {
        return;
    }

    try {

        await api(
            "/tasks",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({

                    agent_id:
                        agentId,

                    action:
                        "uninstall",

                    package:
                        packageName
                })
            }
        );

        alert(
            "Deinstallation wurde gestartet."
        );

        await loadTasks();

    } catch (error) {

        alert(
            "Fehler: " +
            error.message
        );
    }
}


// ============================================================
// CHOOSE AGENT
// ============================================================

async function chooseAgent() {

    try {

        const data =
            await api("/agents");

        const agents =
            data.agents;

        if (!agents.length) {

            alert(
                "Es ist kein Raspberry Pi verbunden."
            );

            return null;
        }

        if (agents.length === 1) {

            return agents[0].agent_id;
        }

        const options =
            agents.map(
                (agent, index) => {

                    return `${index + 1}: ${
                        agent.hostname
                    }`;
                }
            ).join("\n");

        const answer =
            prompt(
                "Welchen Raspberry Pi möchtest du verwenden?\n\n" +
                options
            );

        const index =
            Number(answer) - 1;

        if (
            Number.isNaN(index) ||
            !agents[index]
        ) {

            return null;
        }

        return agents[index].agent_id;

    } catch (error) {

        alert(
            "Fehler beim Laden der Raspberry Pis: " +
            error.message
        );

        return null;
    }
}


// ============================================================
// TASKS
// ============================================================

async function loadTasks() {

    const container =
        document.getElementById(
            "tasks"
        );

    try {

        const data =
            await api("/tasks");

        const tasks =
            data.tasks;

        document.getElementById(
            "taskCount"
        ).textContent =
            tasks.length;

        if (!tasks.length) {

            container.innerHTML =
                `
                <div class="empty">
                    Keine Aufgaben.
                </div>
                `;

            return;
        }

        container.innerHTML =
            tasks
                .slice()
                .reverse()
                .map(task => {

                    return `
                        <div class="task">

                            <strong>
                                ${escapeHtml(
                                    task.action
                                )}
                                ${
                                    task.package
                                    ? " – " +
                                      escapeHtml(
                                          task.package
                                      )
                                    : ""
                                }
                            </strong>

                            <div>
                                Raspberry Pi:
                                ${escapeHtml(
                                    task.agent_id
                                )}
                            </div>

                            <div class="task-status">
                                Status:
                                ${escapeHtml(
                                    task.status
                                )}
                            </div>

                            <small>
                                ${escapeHtml(
                                    task.created_at
                                )}
                            </small>

                        </div>
                    `;

                }).join("");

    } catch (error) {

        container.innerHTML =
            `
            <div class="empty">
                Fehler:
                ${escapeHtml(
                    error.message
                )}
            </div>
            `;
    }
}


// ============================================================
// SECURITY HELPERS
// ============================================================

function escapeHtml(
    value
) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function escapeJs(
    value
) {

    return String(value)
        .replaceAll("\\", "\\\\")
        .replaceAll("'", "\\'");
}


// ============================================================
// START
// ============================================================

async function start() {

    await loadSystem();

    await loadAgents();

    await loadStore();

    await loadTasks();
}


start();


// Alle 15 Sekunden aktualisieren
setInterval(
    async () => {

        await loadSystem();

        await loadAgents();

        await loadTasks();

    },
    15000
);