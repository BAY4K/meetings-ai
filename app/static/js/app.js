const elements = {
    audioFile: document.getElementById(
        "audioFile"
    ),

    speakerCount: document.getElementById(
        "speakerCount"
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

    elements.processButton.disabled = true;

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


    // Если выбран Auto, поле вообще не отправляем.
    //
    // Тогда FastAPI получит: num_speakers = None
    //
    // и Transcriber включит auto mode.
    if (speakerCount) {
        formData.append(
            "num_speakers",
            speakerCount
        );
    }


    try {
        const response = await fetch(
            "/process",
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


        const data =
            await response.json();


        renderResult(data);


        showStatus(
            "Обработка завершена.",
            "success"
        );

    } catch (error) {
        console.error(error);

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


async function getErrorMessage(response) {
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
    elements.resultContainer.classList.remove(
        "hidden"
    );

    elements.transcript.textContent =
        data.transcript || "";

    renderExtraction(
        data.extraction
    );

    if (data.download_url) {
        elements.downloadButton.href =
            data.download_url;

        elements.downloadButton.classList.remove(
            "hidden"
        );
    }
}


function renderExtraction(extraction) {
    elements.protocolBlocks.replaceChildren();

    if (
        !extraction
        || !Array.isArray(extraction.heard)
    ) {
        return;
    }


    for (const block of extraction.heard) {
        elements.protocolBlocks.appendChild(
            createProtocolBlock(block)
        );
    }


    renderWarnings(
        extraction
    );
}


function createProtocolBlock(block) {
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
        getSpeakerName(block);

    container.appendChild(
        speaker
    );


    const summary =
        document.createElement(
            "p"
        );

    summary.className =
        "protocol-summary";

    summary.textContent =
        block.summary || "";

    container.appendChild(
        summary
    );


    const resolutions =
        Array.isArray(block.resolutions)
            ? block.resolutions
            : [];


    if (resolutions.length === 0) {
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


function createResolution(resolution) {
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


        for (const value of metadata) {
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


function getSpeakerName(block) {
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
            resolution.responsible_name
        );
    }


    if (
        resolution.responsible_speaker
    ) {
        return formatSpeakerId(
            resolution
                .responsible_speaker
        );
    }


    return null;
}


function formatSpeakerId(
    speakerId
) {
    if (!speakerId) {
        return "Спикер";
    }


    const match =
        speakerId.match(
            /^SPEAKER_(\d+)$/
        );


    if (!match) {
        return "Спикер";
    }


    return (
        `Спикер ${Number(match[1]) + 1}`
    );
}


function renderWarnings(extraction) {
    elements.warnings.replaceChildren();


    const unresolved =
        Array.isArray(
            extraction
                .unresolved_questions
        )
            ? extraction
                .unresolved_questions
            : [];


    const ambiguous =
        Array.isArray(
            extraction
                .ambiguous_fragments
        )
            ? extraction
                .ambiguous_fragments
            : [];


    if (
        unresolved.length === 0
        && ambiguous.length === 0
    ) {
        elements.warningsCard.classList.add(
            "hidden"
        );

        return;
    }


    elements.warningsCard.classList.remove(
        "hidden"
    );


    if (unresolved.length > 0) {
        elements.warnings.appendChild(
            createWarningGroup(
                "Нерешённые вопросы",
                unresolved
            )
        );
    }


    if (ambiguous.length > 0) {
        elements.warnings.appendChild(
            createWarningGroup(
                "Неоднозначные фрагменты",
                ambiguous
            )
        );
    }
}


function createWarningGroup(
    title,
    values
) {
    const group =
        document.createElement(
            "section"
        );

    group.className =
        "warning-group";


    const heading =
        document.createElement(
            "h3"
        );

    heading.textContent =
        title;

    group.appendChild(
        heading
    );


    for (const value of values) {
        const warning =
            document.createElement(
                "div"
            );

        warning.className =
            "warning";

        warning.textContent =
            value;

        group.appendChild(
            warning
        );
    }


    return group;
}


function showStatus(
    message,
    type = null
) {
    elements.statusCard.classList.remove(
        "hidden"
    );

    elements.statusText.textContent =
        message;

    elements.statusText.classList.remove(
        "success",
        "error"
    );


    if (type) {
        elements.statusText.classList.add(
            type
        );
    }
}


function resetResult() {
    elements.resultContainer.classList.add(
        "hidden"
    );


    elements.protocolBlocks.replaceChildren();

    elements.warnings.replaceChildren();


    elements.warningsCard.classList.add(
        "hidden"
    );


    elements.transcript.textContent =
        "";


    elements.downloadButton.classList.add(
        "hidden"
    );


    elements.downloadButton.removeAttribute(
        "href"
    );
}