const elements = {
    audioFile: document.getElementById(
        "audioFile"
    ),

    speakerCount: document.getElementById(
        "speakerCount"
    ),

    hotwords: document.getElementById(
        "hotwords"
    ),

    processButton: document.getElementById(
        "processButton"
    ),

    statusCard: document.getElementById(
        "statusCard"
    ),

    statusText: document.getElementById(
        "statusText"
    ),

    resultContainer: document.getElementById(
        "resultContainer"
    ),

    protocolBlocks: document.getElementById(
        "protocolBlocks"
    ),

    warningsCard: document.getElementById(
        "warningsCard"
    ),

    warnings: document.getElementById(
        "warnings"
    ),

    transcript: document.getElementById(
        "transcript"
    ),

    downloadButton: document.getElementById(
        "downloadButton"
    ),
};


elements.processButton.addEventListener(
    "click",
    processMeeting
);


async function processMeeting() {
    const file =
        elements.audioFile.files[0];

    if (!file) {
        showStatus(
            "Сначала выберите аудиофайл.",
            "error"
        );

        return;
    }

    resetResult();

    elements.processButton.disabled =
        true;

    showStatus(
        "Обработка записи. "
        + "Это может занять несколько минут..."
    );


    const formData = new FormData();

    formData.append(
        "file",
        file
    );

    const speakerCount =
        elements.speakerCount.value;


    // Если выбран Auto, поле
    // вообще не отправляем.
    if (speakerCount) {
        formData.append(
            "num_speakers",
            speakerCount
        );
    }


    const hotwords =
        elements.hotwords.value.trim();

    if (hotwords) {
        formData.append(
            "hotwords",
            hotwords
        );
    }


    try {
        const response = await fetch(
            "/process/jobs",
            {
                method: "POST",
                body: formData,
            }
        );


        if (!response.ok) {
            throw new Error(
                await getErrorMessage(
                    response
                )
            );
        }

        const job =
            await response.json();

        showStatus(
            job.message
            || "Задача создана..."
        );

        const result =
            await waitForJob(
                job.status_url
            );


        renderResult(
            result
        );

        showStatus(
            "Обработка завершена.",
            "success"
        );

    } catch (error) {
        console.error(
            error
        );

        showStatus(
            error.message
            || "Не удалось обработать запись.",
            "error"
        );

    } finally {
        elements.processButton.disabled =
            false;
    }
}


async function waitForJob(
    statusUrl
) {
    while (true) {
        const response = await fetch(
            statusUrl,
            {
                method: "GET",
            }
        );

        if (!response.ok) {
            throw new Error(
                await getErrorMessage(
                    response
                )
            );
        }

        const job =
            await response.json();


        if (job.message) {
            showStatus(
                job.message
            );
        }


        if (
            job.status ===
            "completed"
        ) {
            if (!job.result) {
                throw new Error(
                    "Задача завершена, "
                    + "но сервер не вернул результат."
                );
            }

            return job.result;
        }


        if (
            job.status ===
            "failed"
        ) {
            throw new Error(
                job.error
                || job.message
                || "Обработка завершилась ошибкой."
            );
        }


        if (
            job.status !== "queued"
            && job.status !== "running"
        ) {
            throw new Error(
                `Неизвестный статус задачи: ${job.status}`
            );
        }


        await sleep(
            5000
        );
    }
}


function sleep(ms) {
    return new Promise(
        resolve => setTimeout(
            resolve,
            ms
        )
    );
}


async function getErrorMessage(
    response
) {
    try {
        const data =
            await response.json();

        if (data.detail) {
            return data.detail;
        }

    } catch {
        // Сервер вернул не JSON.
    }

    return (
        `Ошибка сервера: ${response.status}`
    );
}


function renderResult(data) {
    elements
        .resultContainer
        .classList
        .remove("hidden");


    elements.transcript.textContent =
        data.transcript || "";


    renderExtraction(
        data.extraction
    );


    if (data.download_url) {
        elements.downloadButton.href =
            data.download_url;

        elements
            .downloadButton
            .classList
            .remove("hidden");
    }
}


// CHANGED:
// Новый extraction содержит:
// protocol_blocks + manual_review.
function renderExtraction(
    extraction
) {
    elements
        .protocolBlocks
        .replaceChildren();

    if (!extraction) {
        return;
    }


    const blocks =
        Array.isArray(
            extraction.protocol_blocks
        )
            ? extraction.protocol_blocks
            : [];


    for (const block of blocks) {
        elements
            .protocolBlocks
            .appendChild(
                createProtocolBlock(
                    block
                )
            );
    }


    renderManualReview(
        extraction.manual_review
    );
}


function createProtocolBlock(
    block
) {
    const container =
        document.createElement(
            "article"
        );

    container.className =
        "protocol-block";


    const speaker =
        document.createElement(
            "h3"
        );

    speaker.className =
        "protocol-speaker";

    speaker.textContent =
        getSpeakerName(
            block
        );

    container.appendChild(
        speaker
    );


    const content =
        document.createElement(
            "p"
        );

    // CSS-класс оставляем старым,
    // чтобы не пришлось менять
    // styles.css.
    //
    // По смыслу это уже НЕ summary.
    content.className =
        "protocol-summary";

    // CHANGED:
    // summary -> content.
    content.textContent =
        block.content || "";

    container.appendChild(
        content
    );


    const resolutions =
        Array.isArray(
            block.resolutions
        )
            ? block.resolutions
            : [];


    // Если итогового решения нет,
    // заголовок "Решение" не выводим.
    if (
        resolutions.length === 0
    ) {
        return container;
    }


    const resolutionLabel =
        document.createElement(
            "div"
        );

    resolutionLabel.className =
        "protocol-label";

    resolutionLabel.textContent =
        "Решение:";

    container.appendChild(
        resolutionLabel
    );


    for (
        const resolution
        of resolutions
    ) {
        container.appendChild(
            createResolution(
                resolution
            )
        );
    }


    return container;
}


function createResolution(
    resolution
) {
    const container =
        document.createElement(
            "div"
        );

    container.className =
        "resolution";


    const text =
        document.createElement(
            "div"
        );

    text.className =
        "resolution-text";

    text.textContent =
        resolution.text || "";

    container.appendChild(
        text
    );


    const metadata = [];


    const responsible =
        getResponsibleName(
            resolution
        );


    if (responsible) {
        metadata.push(
            `Ответственный: ${responsible}`
        );
    }


    if (resolution.deadline) {
        metadata.push(
            `Срок: ${resolution.deadline}`
        );
    }


    if (metadata.length > 0) {
        const meta =
            document.createElement(
                "div"
            );

        meta.className =
            "resolution-meta";


        for (
            const value
            of metadata
        ) {
            const item =
                document.createElement(
                    "span"
                );

            item.textContent =
                value;

            meta.appendChild(
                item
            );
        }


        container.appendChild(
            meta
        );
    }


    return container;
}


function getSpeakerName(
    block
) {
    if (block.speaker_name) {
        return block.speaker_name;
    }

    return formatSpeakerId(
        block.speaker_id
    );
}


function getResponsibleName(
    resolution
) {
    if (
        resolution.responsible_name
    ) {
        return (
            resolution
                .responsible_name
        );
    }


    if (
        resolution
            .responsible_speaker
    ) {
        return formatSpeakerId(
            resolution
                .responsible_speaker
        );
    }


    return null;
}


// CHANGED:
// Теперь формат соответствует
// "Спикер №N".
//
// UNKNOWN показываем как
// "Неизвестный спикер".
function formatSpeakerId(
    speakerId
) {
    if (
        speakerId === "UNKNOWN"
    ) {
        return (
            "Неизвестный спикер"
        );
    }


    if (!speakerId) {
        return (
            "Неизвестный спикер"
        );
    }


    const match =
        speakerId.match(
            /^SPEAKER_(\d+)$/
        );


    if (!match) {
        return (
            "Неизвестный спикер"
        );
    }


    return (
        `Спикер №${Number(match[1]) + 1}`
    );
}


// NEW:
// Вместо unresolved_questions
// и ambiguous_fragments показываем
// служебный блок.
function renderManualReview(
    manualReview
) {
    elements.warnings.replaceChildren();

    elements
        .warningsCard
        .classList
        .remove("hidden");


    const items =
        Array.isArray(
            manualReview
        )
            ? manualReview
            : [];


    if (items.length === 0) {
        const empty =
            document.createElement(
                "p"
            );

        empty.className =
            "muted";

        empty.textContent =
            "Сомнительных фрагментов "
            + "не выявлено.";

        elements.warnings.appendChild(
            empty
        );

        return;
    }


    for (const item of items) {
        elements.warnings.appendChild(
            createManualReviewItem(
                item
            )
        );
    }
}


// NEW:
function createManualReviewItem(
    item
) {
    const container =
        document.createElement(
            "div"
        );

    container.className =
        "warning";


    const meta =
        document.createElement(
            "div"
        );

    const timestamp =
        formatTimestamp(
            item.timestamp
        );

    const speaker =
        formatSpeakerId(
            item.speaker_id
        );

    meta.textContent =
        `${timestamp} ${speaker} — `
        + `${item.check_type || "проверка"}`;

    meta.style.fontWeight =
        "bold";

    container.appendChild(
        meta
    );


    const fragment =
        document.createElement(
            "div"
        );

    fragment.textContent =
        item.fragment || "";

    fragment.style.marginTop =
        "6px";

    container.appendChild(
        fragment
    );


    return container;
}


// NEW:
function formatTimestamp(
    timestamp
) {
    if (!timestamp) {
        return "";
    }

    const value =
        String(timestamp)
            .trim()
            .replace(/^\[/, "")
            .replace(/\]$/, "");

    return `[${value}]`;
}


function showStatus(
    message,
    type = null
) {
    elements
        .statusCard
        .classList
        .remove("hidden");


    elements.statusText.textContent =
        message;


    elements
        .statusText
        .classList
        .remove(
            "success",
            "error"
        );


    if (type) {
        elements
            .statusText
            .classList
            .add(type);
    }
}


function resetResult() {
    elements
        .resultContainer
        .classList
        .add("hidden");


    elements
        .protocolBlocks
        .replaceChildren();


    elements
        .warnings
        .replaceChildren();


    elements
        .warningsCard
        .classList
        .add("hidden");


    elements.transcript.textContent =
        "";


    elements
        .downloadButton
        .classList
        .add("hidden");


    elements
        .downloadButton
        .removeAttribute(
            "href"
        );
}