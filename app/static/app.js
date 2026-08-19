const search =
    document.getElementById("search");

const apps =
    document.querySelectorAll(".app-card");

const categories =
    document.getElementById("categories");

const terminal =
    document.getElementById("terminal");

const output =
    document.getElementById("output");


let selectedCategory = "Alle";


function createCategories() {

    const categorySet = new Set();

    apps.forEach(app => {

        categorySet.add(
            app.dataset.category
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


function filterApps() {

    const query =
        search.value
            .trim()
            .toLowerCase();


    apps.forEach(app => {

        const name =
            app.dataset.name;

        const description =
            app.dataset.description;

        const category =
            app.dataset.category;


        const matchesSearch =
            name.includes(query) ||
            description.includes(query);


        const matchesCategory =
            selectedCategory === "Alle" ||
            category === selectedCategory;


        app.style.display =
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


async function installApp(
    appId,
    button
) {

    if (
        !confirm(
            "Diese App auf dem Raspberry Pi installieren?"
        )
    ) {
        return;
    }


    terminal.classList.remove(
        "hidden"
    );


    output.textContent =
        "Installation wird gestartet...\n";


    button.disabled = true;

    button.textContent =
        "Installation läuft...";


    try {

        const response =
            await fetch(
                `/api/install/${appId}`,
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

            button.disabled = false;

            button.textContent =
                "Erneut versuchen";

            return;
        }


        pollStatus(
            button
        );

    } catch (error) {

        output.textContent +=
            "\nVerbindungsfehler: " +
            error;

        button.disabled = false;

        button.textContent =
            "Erneut versuchen";
    }
}


async function pollStatus(
    button
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
                () => pollStatus(button),
                1000
            );

            return;
        }


        if (status.success) {

            button.textContent =
                "✓ Installiert";

            button.classList.add(
                "installed"
            );

            button.disabled =
                true;

        } else {

            button.textContent =
                "Erneut versuchen";

            button.disabled =
                false;

        }

    } catch {

        setTimeout(
            () => pollStatus(button),
            1500
        );
    }
}


createCategories();
