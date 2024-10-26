document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("get-recommendations");
    const recommendationOutput = document.getElementById("recommendation-output");

    form.addEventListener("submit", async function (e) {
        e.preventDefault(); // Prevenir la recarga de la página

        const query = document.getElementById("query").value;

        try {
            // Hacer la solicitud POST a Flask
            const response = await fetch("/get_recommendations", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ query }),
            });

            // Verificar si la respuesta fue exitosa
            if (response.ok) {
                const data = await response.json();
                // Mostrar la respuesta de OpenAI en la página
                recommendationOutput.innerHTML = `<p>${data.recommendation}</p>`;
            } else {
                // Manejar errores si el backend devuelve una respuesta no exitosa
                const errorData = await response.json();
                console.error("Error en la respuesta:", errorData.error);
                recommendationOutput.innerHTML = `<p>Error: ${errorData.error}</p>`;
            }
        } catch (error) {
            console.error("Error obteniendo recomendaciones:", error);
            recommendationOutput.innerHTML = "<p>Error obteniendo recomendaciones. Inténtalo de nuevo.</p>";
        }
    });
});
