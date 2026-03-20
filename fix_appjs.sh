#!/bin/bash
# === REPARADOR DE app.js para Ubuntu ===
# Ejecutar desde la carpeta mini_soc:
#   bash fix_appjs.sh

echo "Reparando static/app.js..."

cat << 'ENDOFFILE' > static/app.js
const API_URL = window.location.origin + "/api";

function formatTime(isoString) {
    const d = new Date(isoString);
    return d.toLocaleString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function getSeverityClass(severity) {
    const s = severity.toLowerCase();
    if (s.includes('crit') || s.includes('high')) return 'critical';
    if (s.includes('med')) return 'medium';
    return 'medium';
}

function renderActionButtons(alert) {
    if (alert.status !== 'Abierta') return '';
    let buttons = '';
    const ipMatch = alert.description.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/);
    const targetIp = ipMatch ? ipMatch[0] : null;

    if (alert.title.includes("Fortinet") || alert.title.includes("Puertos") || alert.title.includes("Malware")) {
        if(targetIp) {
            buttons += '<br><button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 6px; display:block; width:100%; border-color:#ef4444; color:#ef4444;" onclick="soarBlockIp(' + alert.id + ', \'' + targetIp + '\')"><i class="fa-solid fa-ban"></i> Aislar IP (' + targetIp + ')</button>';
        }
        buttons += '<button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 4px; display:block; width:100%; border-color:#f59e0b; color:#f59e0b;" onclick="resolveAlert(' + alert.id + ', \'Falso Positivo - Trafico Interno Autorizado\')"><i class="fa-solid fa-check"></i> Marcar Falso Positivo</button>';
    } else if (alert.title.includes("Windows") || alert.title.includes("Fuerza Bruta")) {
        if(targetIp) {
            buttons += '<br><button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 6px; display:block; width:100%; border-color:#ef4444; color:#ef4444;" onclick="soarBlockIp(' + alert.id + ', \'' + targetIp + '\')"><i class="fa-solid fa-shield-halved"></i> Bloquear Origen FW</button>';
        }
        buttons += '<button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 4px; display:block; width:100%; border-color:#f59e0b; color:#f59e0b;" onclick="resolveAlert(' + alert.id + ', \'Usuario olvido Password - Reset de credenciales aplicado\')"><i class="fa-solid fa-key"></i> Resetear Password AD</button>';
    } else {
        buttons += '<br><button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 6px; display:block; width:100%; border-color:#10b981; color:#10b981;" onclick="resolveAlert(' + alert.id + ')"><i class="fa-solid fa-clipboard-check"></i> Atender (Manual)</button>';
    }
    return buttons;
}

async function fetchAlerts() {
    try {
        const response = await fetch(API_URL + '/alerts');
        if (!response.ok) throw new Error("API error");
        const alerts = await response.json();
        const tbody = document.querySelector("#alertsTable tbody");
        tbody.innerHTML = "";
        let criticalCount = 0;

        if(alerts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #6b7280; padding: 20px;">No hay alertas activas en el sistema :)</td></tr>';
        }

        alerts.forEach(function(alert) {
            if (alert.severity.toLowerCase().includes('crit') || alert.severity.toLowerCase().includes('high')) {
                criticalCount++;
            }
            const tr = document.createElement("tr");
            tr.className = "fade-in";
            tr.innerHTML = '<td style="color: #475569; font-weight: 500;">' + formatTime(alert.timestamp) + '</td>' +
                '<td><span class="badge ' + getSeverityClass(alert.severity) + '">' + alert.severity + '</span></td>' +
                '<td><strong style="color: #0f172a; font-size: 14px;">' + alert.title + '</strong><br>' +
                '<small style="color: #334155; display: block; margin-top: 5px; white-space: pre-wrap; font-size: 13px; font-weight: 500;">' + alert.description + '</small></td>' +
                '<td style="vertical-align: middle;"><span style="font-size: 13px; font-weight: 800; color: ' + (alert.status === 'Abierta' ? '#dc2626' : '#059669') + ';">' + alert.status.toUpperCase() + '</span>' +
                renderActionButtons(alert) + '</td>';
            tbody.appendChild(tr);
        });
        var cEl = document.getElementById("criticalCount");
        if(cEl) cEl.textContent = criticalCount;
    } catch (error) {
        console.error("No se pudo conectar al API de Alertas:", error);
    }
}

async function resolveAlert(id, prefilledNota) {
    var nota = prefilledNota || null;
    if(!nota) {
        nota = prompt("Por favor, ingresa la accion manual realizada (ISO 27001):", "Atendido por Operador SOC");
        if (nota === null) return;
    } else {
        var confirmacion = confirm('SOAR - Aprobar resolucion automatica:\n"' + nota + '"?');
        if(!confirmacion) return;
    }
    try {
        var res = await fetch(API_URL + '/alerts/' + id + '/status?status=Cerrada&note=' + encodeURIComponent(nota), { method: 'PUT' });
        if(res.ok) fetchAlerts();
    } catch(err) {
        console.error("Error gestionando incidente:", err);
    }
}

async function soarBlockIp(alertId, ip) {
    var confirmAction = confirm('ALERTA SOAR: Confirmas que deseas conectar remotamente con Fortinet e inyectar un bloqueo TOTAL para la IP ' + ip + '?');
    if(!confirmAction) return;
    try {
        var res = await fetch(API_URL + '/firewall/block', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: ip })
        });
        if(!res.ok) throw new Error("Falla API FW Bloqueo");
        await fetch(API_URL + '/alerts/' + alertId + '/status?status=Cerrada&note=' + encodeURIComponent('SOAR (Auto): La IP ' + ip + ' se detecto como hostil y fue aislada por el Endpoint en Fortinet.'), { method: 'PUT' });
        window.alert('Exito: IP ' + ip + ' neutralizada y alerta clausurada.');
        fetchAlerts();
    } catch(err) {
        window.alert('Error aislando IP origen: ' + err);
    }
}

fetchAlerts();
fetchGlobalMetrics();
fetchForwardLogs();

setInterval(function() {
    fetchAlerts();
    fetchGlobalMetrics();
    fetchForwardLogs();
}, 3000);

async function fetchGlobalMetrics() {
    try {
        var res = await fetch(API_URL + '/metrics/summary');
        if(res.ok) {
            var data = await res.json();
            var eEl = document.getElementById('topMetricEventos');
            var aEl = document.getElementById('topMetricAlertas');
            var hEl = document.getElementById('topMetricActivos');
            if(eEl) eEl.textContent = data.eventos_hoy;
            if(aEl) aEl.textContent = data.alertas_criticas;
            if(hEl) hEl.textContent = data.activos_vigilados;
        }
    } catch(err) {}
}

async function fetchForwardLogs() {
    var view = document.getElementById('forward-view');
    if(view && view.style.display === 'none') return;
    try {
        var res = await fetch(API_URL + '/logs/forward');
        if(!res.ok) return;
        var logs = await res.json();
        var tbody = document.getElementById('forwardBody');
        if(!tbody) return;

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color: #6b7280; padding: 25px;">Sin trafico Forward capturado por Syslog aun.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        logs.forEach(function(log) {
            var raw = log.raw_log;
            var destip = (raw.match(/dstip=([\d\.]+)/) || [])[1] || 'N/D';
            var action = (raw.match(/action="?([^"\s]+)"?/) || [])[1] || '';
            var app = (raw.match(/app="([^"]+)"/) || [])[1] || 'Web/Trafico Generico';
            var appcat = (raw.match(/appcat="([^"]+)"/) || [])[1] || '';
            if(appcat) appcat = '(' + appcat + ')';

            var actionBadge = '';
            if(action) {
                var badgeClass = 'medium';
                if(action.indexOf('accept') >= 0 || action.indexOf('start') >= 0) badgeClass = 'success';
                else if(action.indexOf('deny') >= 0 || action.indexOf('block') >= 0 || action.indexOf('drop') >= 0) badgeClass = 'critical';
                actionBadge = '<span class="badge ' + badgeClass + '" style="font-size: 10px;">' + action.toUpperCase() + '</span>';
            }

            var detallesFormatted = '<div style="display:flex; justify-content:space-between; align-items:center; width: 100%;">' +
                '<div><span style="color:var(--text-muted); font-size:13px;">Destino / Servidor:</span> ' +
                '<strong style="color:#0284c7; font-size:15px; margin-left:6px;">' + destip + '</strong><br>' +
                '<span style="color:var(--text-muted); font-size:13px;">App Control:</span> ' +
                '<strong style="color:#d97706; font-size:14px; margin-left:6px;">' + app + '</strong> <span style="font-size:12px; color:#64748b;">' + appcat + '</span></div>' +
                '<div>' + actionBadge + '</div></div>';

            var tr = document.createElement('tr');
            tr.innerHTML = '<td style="color: #475569; font-weight: 500; font-size: 13px; white-space:nowrap; vertical-align:middle;">' + formatTime(log.timestamp) + '</td>' +
                '<td style="vertical-align:middle; font-weight:bold; color:#0f172a; font-size:15px;">' + (log.source_ip || 'N/D') + '</td>' +
                '<td style="background-color: #f1f5f9; padding: 12px 18px; border-radius: 8px; border: 1px solid #e2e8f0;">' + detallesFormatted + '</td>';
            tbody.appendChild(tr);
        });
    } catch(err) {}
}

/* === LOGICA DE NAVEGACION DEL DASHBOARD === */
document.querySelectorAll('#mainNav a').forEach(function(link) {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelectorAll('#mainNav a').forEach(function(nav) { nav.classList.remove('active'); });
        e.currentTarget.classList.add('active');
        document.querySelectorAll('.view-section').forEach(function(view) { view.style.display = 'none'; });
        var targetId = e.currentTarget.getAttribute('data-view');
        var targetView = document.getElementById(targetId);
        targetView.style.display = 'block';
        var titleMap = {
            'dashboard-view': 'Monitoreo de Seguridad en Tiempo Real',
            'activos-view': 'Seguridad de Activos (Windows)',
            'firewall-view': 'Administracion Firewall (Fortinet)',
            'forward-view': 'Auditoria de Trafico y Navegacion'
        };
        document.getElementById('pageTitle').textContent = titleMap[targetId];
    });
});

/* === LOGICA DE INTERACTIVIDAD (ACTIVOS & FIREWALL) === */
function fetchHostsDatabase() {
    var tbody = document.getElementById('hostsBody');
    if(!tbody) return;
    fetch(API_URL + '/metrics/hosts')
        .then(function(res) { return res.json(); })
        .then(function(hosts_reales) {
            if (hosts_reales.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color: #6b7280; padding: 25px;">Aun no hay equipos descubiertos. El escaner esta trabajando...</td></tr>';
                return;
            }
            tbody.innerHTML = '';
            hosts_reales.forEach(function(host) {
                var tr = document.createElement('tr');
                tr.className = 'fade-in';
                var hostDisplay = host.hostname && host.hostname !== 'Desconocido' ? host.hostname : 'Dispositivo Generico (Sin DNS)';
                tr.innerHTML = '<td><div style="font-weight: bold; color: var(--primary);"><i class="fa-solid fa-desktop" style="margin-right: 8px; color: #64748b;"></i>' + host.ip + '</div>' +
                    '<div style="font-size: 11px; color: #64748b; margin-left: 22px;">Hostname: <strong style="color:var(--text-main);">' + hostDisplay + '</strong></div></td>' +
                    '<td><span class="badge success">Online Activo</span></td>' +
                    '<td style="color: #64748b; font-weight: 600;">' + host.last_seen + '</td>' +
                    '<td id="actions-' + host.ip.replace(/\./g, '-') + '"><button class="btn-outline" style="padding: 4px 10px; font-size: 11px;" onclick="scanPorts(\'' + host.ip + '\')">Escanear Puertos</button></td>';
                tbody.appendChild(tr);
            });
        })
        .catch(function(err) { console.error('Error auto-fetching hosts:', err); });
}

var btnScan = document.getElementById('btnScan');
if(btnScan) {
    btnScan.addEventListener('click', function() {
        var progress = document.getElementById('scanProgress');
        var bar = document.getElementById('scanBar');
        var percentTxt = document.getElementById('scanPercent');
        btnScan.disabled = true;
        btnScan.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Auditando Trafico...';
        progress.style.display = 'block';
        bar.style.width = '0%';
        var percent = 0;
        var interval = setInterval(function() {
            percent += Math.floor(Math.random() * 20) + 5;
            if(percent >= 100) percent = 100;
            bar.style.width = percent + '%';
            percentTxt.textContent = percent;
            if (percent === 100) {
                clearInterval(interval);
                btnScan.disabled = false;
                btnScan.innerHTML = '<i class="fa-solid fa-radar"></i> Iniciar Barrido de Red';
                progress.style.display = 'none';
                fetchHostsDatabase();
            }
        }, 120);
    });
    setInterval(fetchHostsDatabase, 300000);
    setTimeout(fetchHostsDatabase, 1500);
}

async function scanPorts(ip) {
    var actionTd = document.getElementById('actions-' + ip.replace(/\./g, '-'));
    if(!actionTd) return;
    var btn = actionTd.querySelector('button');
    if(btn) { btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Auditando...'; btn.disabled = true; }
    try {
        var res = await fetch(API_URL + '/metrics/scan_ports/' + ip);
        if(!res.ok) throw new Error("API Falla");
        var data = await res.json();
        if (data.open_ports.length === 0) {
            actionTd.innerHTML = '<span style="color: #10b981; font-weight: bold; font-size: 11px;"><i class="fa-solid fa-shield-halved"></i> Seguro (Cerrados)</span>';
        } else {
            var pills = '';
            data.open_ports.forEach(function(p) {
                var isCrit = (p.indexOf('3389') >= 0 || p.indexOf('445') >= 0 || p.indexOf('22') >= 0);
                var color = isCrit ? '#ef4444' : '#f59e0b';
                pills += '<span style="background:' + color + '; color:white; padding: 2px 6px; border-radius:4px; font-size: 10px; font-weight: bold; margin-right: 4px; display:inline-block; margin-bottom:2px;">' + p + '</span>';
            });
            actionTd.innerHTML = pills;
        }
    } catch(err) {
        if(btn) { btn.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Error API'; btn.disabled = false; }
    }
}

var btnPing = document.getElementById('btnPingFw');
if(btnPing) {
    btnPing.addEventListener('click', async function(e) {
        var btn = e.currentTarget;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Conectando...';
        btn.style.borderColor = '#f59e0b';
        btn.style.color = '#f59e0b';
        try {
            var res = await fetch(API_URL + '/firewall/ping');
            if(!res.ok) throw new Error("Status " + res.status);
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Firewall En Linea';
            btn.style.borderColor = '#10b981';
            btn.style.color = '#10b981';
        } catch(err) {
            btn.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Firewall Inalcanzable';
            btn.style.borderColor = '#ef4444';
            btn.style.color = '#ef4444';
        }
        setTimeout(function() {
            btn.innerHTML = '<i class="fa-solid fa-network-wired"></i> Probar Conexion API';
            btn.style.borderColor = 'var(--primary)';
            btn.style.color = 'var(--primary)';
        }, 5000);
    });
}

var btnBlock = document.getElementById('btnBlock');
if(btnBlock) {
    btnBlock.addEventListener('click', async function() {
        var ipTarget = document.getElementById('ipTarget');
        if(!ipTarget.value.trim()) { ipTarget.focus(); return; }
        var ip = ipTarget.value.trim();
        btnBlock.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Inyectando Regla...';
        btnBlock.disabled = true;
        try {
            var res = await fetch(API_URL + '/firewall/block', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip: ip })
            });
            if(!res.ok) throw new Error("Falla API Fortinet");
            var data = await res.json();
            var msgEl = document.getElementById('blockMsg');
            msgEl.textContent = 'Exito: ' + data.message;
            msgEl.style.color = '#10b981';
            msgEl.style.display = 'block';
        } catch (err) {
            var msgEl = document.getElementById('blockMsg');
            msgEl.textContent = 'Error aislando IP ' + ip + '. Verifica API Key y conexion HTTPS.';
            msgEl.style.color = '#ef4444';
            msgEl.style.display = 'block';
        }
        btnBlock.innerHTML = '<i class="fa-solid fa-ban"></i> Aislar IP en Firewall';
        btnBlock.disabled = false;
        ipTarget.value = '';
        setTimeout(function() { document.getElementById('blockMsg').style.display = 'none'; }, 7000);
    });
}

// Filtros en Tiempo Real
var searchAlerts = document.getElementById('searchAlerts');
if(searchAlerts) {
    searchAlerts.addEventListener('input', function(e) {
        var term = e.target.value.toLowerCase();
        document.querySelectorAll('#alertsTable tbody tr').forEach(function(row) {
            var text = row.textContent.toLowerCase();
            row.style.display = text.indexOf(term) >= 0 ? '' : 'none';
        });
    });
}

var searchHosts = document.getElementById('searchHosts');
if(searchHosts) {
    searchHosts.addEventListener('input', function(e) {
        var term = e.target.value.toLowerCase();
        document.querySelectorAll('#hostsTable tbody tr').forEach(function(row) {
            if(row.children.length === 1) return;
            var text = row.textContent.toLowerCase();
            row.style.display = text.indexOf(term) >= 0 ? '' : 'none';
        });
    });
}

var searchForward = document.getElementById('searchForward');
if(searchForward) {
    searchForward.addEventListener('input', function(e) {
        var term = e.target.value.toLowerCase();
        document.querySelectorAll('#forwardTable tbody tr').forEach(function(row) {
            if(row.children.length === 1) return;
            var text = row.children[1].textContent.toLowerCase();
            row.style.display = text.indexOf(term) >= 0 ? '' : 'none';
        });
    });
}

// Exportacion y Reportes
var btnExport = document.getElementById('btnExport');
if(btnExport) {
    btnExport.addEventListener('click', function(e) {
        var btn = e.currentTarget;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generando CSV...';
        btn.disabled = true;
        window.location.href = API_URL + '/metrics/export_csv';
        setTimeout(function() {
            btn.innerHTML = '<i class="fa-solid fa-check"></i> CSV Descargado';
            btn.style.backgroundColor = '#059669';
            setTimeout(function() {
                btn.innerHTML = '<i class="fa-solid fa-file-excel"></i> Exportar Excel';
                btn.disabled = false;
                btn.style.backgroundColor = '';
            }, 3000);
        }, 1500);
    });
}

var btnPdf = document.getElementById('btnPdf');
if(btnPdf) {
    btnPdf.addEventListener('click', function(e) {
        var btn = e.currentTarget;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparando Impresion...';
        btn.disabled = true;
        setTimeout(function() {
            window.print();
            btn.innerHTML = '<i class="fa-solid fa-file-pdf"></i> Generar PDF';
            btn.disabled = false;
        }, 1000);
    });
}

// ====== INITIALIZATION OF CHARTS ======
var attacksChartInstance = null;
var portsChartInstance = null;

async function initCharts() {
    if(attacksChartInstance) return;
    var ctxAttacks = document.getElementById('attacksChart');
    var ctxPorts = document.getElementById('portsChart');
    if(!ctxAttacks || !ctxPorts) return;
    Chart.defaults.color = '#64748b';
    Chart.defaults.font.family = 'Inter';
    try {
        var response = await fetch(API_URL + '/metrics/dashboard');
        if(!response.ok) throw new Error("API error fetching metrics");
        var metrics = await response.json();
        attacksChartInstance = new Chart(ctxAttacks, {
            type: 'bar',
            data: {
                labels: metrics.top_ips.labels,
                datasets: [{ label: 'Ataques Registrados', data: metrics.top_ips.data, backgroundColor: 'rgba(26, 54, 115, 0.85)', borderColor: '#1a3673', borderWidth: 1, borderRadius: 6 }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } } }
        });
        portsChartInstance = new Chart(ctxPorts, {
            type: 'doughnut',
            data: {
                labels: metrics.top_ports.labels,
                datasets: [{ data: metrics.top_ports.data, backgroundColor: ['#ef4444','#f59e0b','#10b981','#94a3b8','#0284c7'], borderWidth: 3, borderColor: '#ffffff', hoverOffset: 4 }]
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15 } } } }
        });
    } catch(err) {
        console.error("No se pudo conectar al API de Metricas:", err);
    }
}

document.querySelectorAll('#mainNav a').forEach(function(link) {
    link.addEventListener('click', function(e) {
        var targetId = e.currentTarget.getAttribute('data-view');
        if(targetId === 'firewall-view') {
            setTimeout(initCharts, 100);
        }
    });
});
ENDOFFILE

echo ""
echo "=== app.js REPARADO EXITOSAMENTE ==="
echo "Recarga tu navegador con Ctrl+Shift+F5"
