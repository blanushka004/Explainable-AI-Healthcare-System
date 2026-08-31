const featureLabels = {
    age: "Age",
    sex: "Sex",
    cp: "Chest Pain Type",
    trestbps: "Resting Blood Pressure",
    chol: "Cholesterol",
    fbs: "Fasting Blood Sugar",
    restecg: "Resting ECG",
    thalach: "Maximum Heart Rate",
    exang: "Exercise-Induced Angina",
    oldpeak: "ST Depression (Oldpeak)",
    slope: "ST Slope",
    ca: "Major Vessels (CA)",
    thal: "Thalassemia Test Result"
};

const API_BASE_URL = "http://127.0.0.1:8000";

function getErrorMessage(detail) {
    if (Array.isArray(detail)) {
        return detail.map(item => item.msg || "Invalid input.").join(" ");
    }
    return typeof detail === "string" ? detail : "The healthcare API could not process the request.";
}

async function predictRisk() {
    const patientData = {
        age: Number(document.getElementById("age").value),
        sex: Number(document.getElementById("sex").value),
        cp: Number(document.getElementById("cp").value),
        trestbps: Number(document.getElementById("trestbps").value),
        chol: Number(document.getElementById("chol").value),
        fbs: Number(document.getElementById("fbs").value),
        restecg: Number(document.getElementById("restecg").value),
        thalach: Number(document.getElementById("thalach").value),
        exang: Number(document.getElementById("exang").value),
        oldpeak: Number(document.getElementById("oldpeak").value),
        slope: Number(document.getElementById("slope").value),
        ca: Number(document.getElementById("ca").value),
        thal: Number(document.getElementById("thal").value)
    };

    if (Object.values(patientData).some(value => !Number.isFinite(value))) {
        alert("Enter a valid numeric value for every patient feature.");
        return;
    }

    const predictButton = document.getElementById("predictButton");
    predictButton.disabled = true;
    predictButton.textContent = "Calculating...";

    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(patientData)
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(getErrorMessage(result.detail));
        }

        displayResult(result);
        loadHistory();
    } catch (error) {
        alert(
            error.message ||
            "Unable to connect to healthcare API. Make sure the FastAPI server is running."
        );
        console.error(error);
    } finally {
        predictButton.disabled = false;
        predictButton.textContent = "Predict Heart Risk";
    }
}

function displayResult(data) {
    document.getElementById("result").classList.remove("hidden");

    const riskSummary = data.risk_summary;
    const riskBox = document.getElementById("riskBox");
    let riskClass = "low-risk";

    if (riskSummary.level === "HIGH") {
        riskClass = "high-risk";
    } else if (riskSummary.level === "MEDIUM") {
        riskClass = "medium-risk";
    }

    riskBox.innerHTML = `
        <h2>${data.prediction}</h2>
        <p>Risk Score: <b>${riskSummary.score}%</b></p>
        <p>Heart-disease probability: <b>${(Number(data.probability) * 100).toFixed(2)}%</b></p>
        <p>Risk Level: <b class="${riskClass}">${riskSummary.level}</b></p>
        <p>Severity: <b class="${riskClass}">${riskSummary.severity}</b></p>
    `;

    document.getElementById("warning").innerText = data.early_warning;

    const recommendationBox = document.getElementById("recommendations");
    recommendationBox.innerHTML = "";
    data.recommendations.forEach(item => {
        recommendationBox.innerHTML += `
            <div class="recommendation-card">
                <h4>${item.title}</h4>
                <p><b>Priority:</b> ${item.priority}</p>
        <p>${item.reason || item.description || "Consult a healthcare professional for personalized guidance."}</p>
            </div>
        `;
    });

    renderFactorAnalysis(
        data.factors_increasing_risk || [],
        data.factors_decreasing_risk || []
    );

    const explainabilityStatus = document.getElementById("explainabilityStatus");
    if (data.explainability_status === "unavailable") {
        explainabilityStatus.textContent = "SHAP factors are temporarily unavailable for this prediction; the model result and recommendations are still available.";
        explainabilityStatus.classList.remove("hidden");
    } else {
        explainabilityStatus.textContent = "";
        explainabilityStatus.classList.add("hidden");
    }
}

function renderFactorAnalysis(increasingFactors, decreasingFactors) {
    const riskFactors = document.getElementById("riskFactors");
    const safeFactors = document.getElementById("safeFactors");
    const allFactors = [...increasingFactors, ...decreasingFactors];
    const maxContribution = Math.max(
        0,
        ...allFactors.map(item => Math.abs(Number(item.shap_contribution) || 0))
    );

    const renderFactors = (container, factors, direction) => {
        if (factors.length === 0) {
            const description = direction === "increasing"
                ? "increasing"
                : "risk-reducing";
            container.innerHTML = `<p class="factor-empty">No major ${description} factors detected.</p>`;
            return;
        }

        container.innerHTML = factors.map(item => {
            const contribution = Number(item.shap_contribution) || 0;
            const percentage = maxContribution > 0
                ? (Math.abs(contribution) / maxContribution) * 100
                : 0;
            const label = featureLabels[item.feature] || item.feature;
            const indicator = direction === "increasing" ? "&#9650;" : "&#9660;";
            const signedValue = `${contribution > 0 ? "+" : ""}${contribution.toFixed(3)}`;

            return `
                <article class="factor-item factor-item--${direction}">
                    <div class="factor-label">
                        <span class="factor-name"><span class="factor-indicator" aria-hidden="true">${indicator}</span>${label}</span>
                        <span class="factor-value">${signedValue}</span>
                    </div>
                    <div class="bar-container" aria-label="${label}: ${signedValue} SHAP contribution">
                        <div class="risk-bar ${direction}" style="width: ${percentage}%"></div>
                    </div>
                </article>
            `;
        }).join("");
    };

    renderFactors(riskFactors, increasingFactors, "increasing");
    renderFactors(safeFactors, decreasingFactors, "decreasing");
}

async function loadHistory() {
    const historyStatus = document.getElementById("historyStatus");
    const historyTable = document.getElementById("historyTable");
    const historyBody = document.getElementById("historyBody");
    historyStatus.textContent = "Loading saved predictions...";

    try {
        const response = await fetch(`${API_BASE_URL}/history?limit=20`);
        const records = await response.json();
        if (!response.ok) {
            throw new Error(getErrorMessage(records.detail));
        }

        if (records.length === 0) {
            historyStatus.textContent = "No saved predictions yet.";
            historyTable.classList.add("hidden");
            return;
        }

        historyBody.innerHTML = records.map(record => {
            const date = record.created_at ? new Date(record.created_at).toLocaleString() : "—";
            const probability = `${(Number(record.probability) * 100).toFixed(2)}%`;
            return `<tr><td>${date}</td><td>${record.age}</td><td>${record.prediction}</td><td>${probability}</td><td>${record.risk_level}</td></tr>`;
        }).join("");
        historyStatus.textContent = `${records.length} saved prediction${records.length === 1 ? "" : "s"}.`;
        historyTable.classList.remove("hidden");
    } catch (error) {
        historyTable.classList.add("hidden");
        historyStatus.textContent = error.message || "Could not load prediction history.";
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", loadHistory);
