function copyTableToClipboard(tableId) {
    const table = document.getElementById(tableId);
    let markdown = "";
    const headers = Array.from(table.querySelectorAll("thead th")).map(th => th.innerText);
    markdown += `| ${headers.join(" | ")} |\n`;
    markdown += `| ${headers.map(() => '---').join(" | ")} |\n`;
    const rows = Array.from(table.querySelectorAll("tbody tr"));
    for (const row of rows) {
        const cells = Array.from(row.querySelectorAll("td")).map(td => td.innerText);
        markdown += `| ${cells.join(" | ")} |\n`;
    }
    navigator.clipboard.writeText(markdown).then(() => alert("Table copied to clipboard as Markdown!"));
}

function copyJsonToClipboard() {
    const jsonText = document.getElementById("json-export").value;
    navigator.clipboard.writeText(jsonText).then(() => alert("JSON copied to clipboard!"));
}