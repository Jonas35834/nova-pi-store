const search =
    document.getElementById("search");

const appsContainer =
    document.getElementById("apps");

const categories =
    document.getElementById("categories");

const terminal =
    document.getElementById("terminal");

const output =
    document.getElementById("output");

const installedCount =
    document.getElementById("installed-count");


let selectedCategory = "Alle";

let appCards = [];


// ============================================================
// KATEGORIEN
// ============================================================

function createCategories() {

    const categorySet =
        new Set();

    appCards.forEach(card => {

        categorySet.add(
            card.dataset.category
        );

    });


    categorySet.forEach(category => {

        const button =
            document.createElement("button");

        button.className =
            "category";

        button.textContent =
            category;

        button.dataset.category =
            category;


        button.addEventListener(
            "click",
            () => {

                selectedCategory =
                    category;


                document
                    .querySelectorAll(
                        ".category"
                    )
                    .forEach(item => {

                        item.classList.remove(
                            "active"
                        );

                    });


                button.classList.add(
                    "active"
                );


                filterApps();

            }
        );


        categories.appendChild(
            button
        );

    });
}


// ============================================================
// SUCHE / FILTER
// ============================================================

function filterApps() {

    const query =
        search.value
            .trim()
            .toLowerCase();


    appCards.forEach(card => {

        const name =
            card.dataset.name;

        const description =
            card.dataset.description;

        const category =
            card.dataset.category;


        const matchesSearch =
            name.includes(query) ||
            description.includes(query);


        const matchesCategory =
            selectedCategory === "Alle" ||
            category === selectedCategory;


        card.style.display =
            matchesSearch &&
            matchesCategory
                ? ""
                : "none";

    });
}


search.addEventListener(
    "input",
    filterApps
);


// ============================================================
// APP AKTION
// ============================================================

async function performAction(
    appId,
    action
) {

    const card =
        document.querySelector(
            `.app-card[data-id="${appId}"]`
        );


    if (!card) {
        return;
    }


    const buttons =
        card.querySelectorAll(
            "button"
        );


    buttons.forEach(button => {
        button.disabled = true;
    });


    const actionButton =
        card.querySelector(
            `.action-${action}`
        );


    if (actionButton) {

        if (action === "install") {
            actionButton.textContent =
                "Installation läuft...";
        }

        if (action === "remove") {
            actionButton.textContent =
                "Deinstallation läuft...";
        }

        if (action === "update") {
            actionButton.textContent =
                "Update läuft...";
        }

    }


    terminal.classList.remove(
        "hidden"
    );


    output.textContent =
        "Aktion wird gestartet...\n";


    try {

        const response =
            await fetch(
                `/api/${action}/${appId}`,
                {
                    method: "POST"
                }
            );


        const result =
            await response.json();


        if (!result.success) {

            output.textContent +=
                "\nFEHLER: " +
                result.error;


            buttons.forEach(button => {
                button.disabled = false;
            });


            return;
        }


        pollStatus(
            appId,
            action
        );


    } catch (error) {

        output.textContent +=
            "\nVerbindungsfehler: " +
            error;


        buttons.forEach(button => {
            button.disabled = false;
        });

    }
}


// ============================================================
// STATUS ABFRAGEN
// ============================================================

async function pollStatus(
    appId,
    action
) {

    try {

        const response =
            await fetch(
                "/api/status"
            );


        const status =
            await response.json();


        output.textContent =
            status.output || "";


        output.scrollTop =
            output.scrollHeight;


        if (status.running) {

            setTimeout(
                () => pollStatus(
                    appId,
                    action
                ),
                1000
            );

            return;
        }


        if (status.success) {

            output.textContent +=
                "\n✓ Vorgang erfolgreich abgeschlossen.";


            setTimeout(
                () => {
                    location.reload();
                },
                1000
            );


        } else {

            const card =
                document.querySelector(
                    `.app-card[data-id="${appId}"]`
                );


            if (card) {

                card
                    .querySelectorAll("button")
                    .forEach(button => {

                        button.disabled =
                            false;

                    });

            }

        }


    } catch (error) {

        setTimeout(
            () => pollStatus(
                appId,
                action
            ),
            1500
        );

    }
}


// ============================================================
// BESTÄTIGUNG
// ============================================================

function installApp(appId) {

    if (
        !confirm(
            "Diese App auf dem Raspberry Pi installieren?"
        )
    ) {
        return;
    }


    performAction(
        appId,
        "install"
    );
}


function removeApp(appId) {

    if (
        !confirm(
            "Diese App wirklich deinstallieren?"
        )
    ) {
        return;
    }


    performAction(
        appId,
        "remove"
    );
}


function updateApp(appId) {

    if (
        !confirm(
            "Diese App aktualisieren?"
        )
    ) {
        return;
    }


    performAction(
        appId,
        "update"
    );
}


// ============================================================
// INSTALLIERTE APPS
// ============================================================

function updateInstalledCount() {

    const installed =
        appCards.filter(card =>
            card.dataset.installed === "true"
        ).length;


    if (installedCount) {

        installedCount.textContent =
            installed;

    }
}


// ============================================================
// START
// ============================================================

appCards = [
    ...document.querySelectorAll(
        ".app-card"
    )
];


createCategories();

filterApps();

updateInstalledCount();
