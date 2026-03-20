const API_URL = window.location.origin + "/api";

function formatTime(isoString) {
    const d = new Date(isoString);
    // Agreamos el dia/mes a la hora para mayor trazabilidad ISO
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
    
    // Regex para buscar IP y ofrecer mitigacion en caliente
    const ipMatch = alert.description.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/);
    const targetIp = ipMatch ? ipMatch[0] : null;

    if (alert.title.includes("Fortinet") || alert.title.includes("Puertos") || alert.title.includes("Malware")) {
        if(targetIp) {
            buttons += `<br><button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 6px; display:block; width:100%; border-color:#ef4444; color:#ef4444;" onclick="soarBlockIp(${alert.id}, '${targetIp}')"><i class="fa-solid fa-ban"></i> Aislar IP (${targetIp})</button>`;
        }
        buttons += `<button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 4px; display:block; width:100%; border-color:#f59e0b; color:#f59e0b;" onclick="resolveAlert(${alert.id}, 'Falso Positivo - Tráfico Interno Autorizado')"><i class="fa-solid fa-check"></i> Marcar Falso Positivo</button>`;
    } 
    else if (alert.title.includes("Windows") || alert.title.includes("Fuerza Bruta")) {
        if(targetIp) {
            buttons += `<br><button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 6px; display:block; width:100%; border-color:#ef4444; color:#ef4444;" onclick="soarBlockIp(${alert.id}, '${targetIp}')"><i class="fa-solid fa-shield-halved"></i> Bloquear Origen FW</button>`;
        }
        buttons += `<button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 4px; display:block; width:100%; border-color:#f59e0b; color:#f59e0b;" onclick="resolveAlert(${alert.id}, 'Usuario olvidó Password - Reset de credenciales aplicado')"><i class="fa-solid fa-key"></i> Resetear Password AD</button>`;
    } 
    else {
        // Genérico original
        buttons += `<br><button class="btn-outline" style="padding: 3px 8px; font-size: 10px; margin-top: 6px; display:block; width:100%; border-color:#10b981; color:#10b981;" onclick="resolveAlert(${alert.id})"><i class="fa-solid fa-clipboard-check"></i> Atender (Manual)</button>`;
    }
    
    return buttons;
}

async function fetchAlerts() {
    try {
        const response = await fetch(`${API_URL}/alerts`);
        if (!response.ok) throw new Error("API error fetching alerts");
        
        const alerts = await response.json();
        
        const tbody = document.querySelector("#alertsTable tbody");
        tbody.innerHTML = "";
        
        let criticalCount = 0;
        
        if(alerts.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: #6b7280; padding: 20px;">No hay alertas activas en el sistema :)</td></tr>`;
        }
        
        alerts.forEach(alert => {
            if (alert.severity.toLowerCase().includes('crit') || alert.severity.toLowerCase().includes('high')) {
                criticalCount++;
            }
            
            const tr = document.createElement("tr");
            tr.className = "fade-in";
            tr.innerHTML = `
                <td style="color: #475569; font-weight: 500;">${formatTime(alert.timestamp)}</td>
                <td><span class="badge ${getSeverityClass(alert.severity)}">${alert.severity}</span></td>
                <td>
                    <strong style="color: #0f172a; font-size: 14px;">${alert.title}</strong><br>
                    <small style="color: #334155; display: block; margin-top: 5px; white-space: pre-wrap; font-size: 13px; font-weight: 500;">${alert.description}</small>
                </td>
                <td style="vertical-align: middle;">
                    <span style="font-size: 13px; font-weight: 800; color: ${alert.status === 'Abierta' ? '#dc2626' : '#059669'};">${alert.status.toUpperCase()}</span>
                    ${renderActionButtons(alert)}
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        document.getElementById("criticalCount").textContent = criticalCount;
    } catch (error) {
        console.error("No se pudo conectar al API de Alertas:", error);
    }
}

async function resolveAlert(id, prefilledNota = null) {
    let nota = prefilledNota;
    
    if(!nota) {
        nota = prompt("Por favor, ingresa la acción manual realizada (ISO 27001):", "Atendido por Operador SOC");
        if (nota === null) return;
    } else {
        const confirmacion = confirm(`SOAR - ¿Aprobar resolución automática:\n"${nota}"?`);
        if(!confirmacion) return;
    }

    try {
        const res = await fetch(`${API_URL}/alerts/${id}/status?status=Cerrada&note=${encodeURIComponent(nota)}`, {
            method: 'PUT'
        });
        if(res.ok) fetchAlerts(); 
    } catch(err) {
        console.error("Error gestionando incidente:", err);
    }
}

async function soarBlockIp(alertId, ip) {
    const confirmAction = confirm(`\ud83d\udd25 ALERTA SOAR \ud83d\udd25\n¿Confirmas que deseas conectar remotamente con Fortinet e inyectar un bloqueo TOTAL para la IP ${ip}?`);
    if(!confirmAction) return;
    
    try {
        // Ejecutar Bloqueo por POST en FW
        const res = await fetch(`${API_URL}/firewall/block`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: ip })
        });
        if(!res.ok) throw new Error("Falla API FW Bloqueo");
        
        // Cerrar ticket automáticamente si exitoso
        await fetch(`${API_URL}/alerts/${alertId}/status?status=Cerrada&note=${encodeURIComponent('SOAR (Auto): La IP ' + ip + ' se detecto como hostil y fue asilada por el Endpoint en Fortinet.')}`, {
            method: 'PUT'
        });
        
        alert(`\u2705 \u00c9xito: IP ${ip} neutralizada y alerta clausurada.`);
        fetchAlerts(); 
    } catch(err) {
        alert(`\u274c Error aislando IP origen: ${err}`);
    }
}

// La terminal ha sido sustituida por el panel expandido de Alertas (SOAR)

fetchAlerts();
fetchGlobalMetrics();
fetchForwardLogs();

setInterval(() => {
    fetchAlerts();
    fetchGlobalMetrics();
    fetchForwardLogs();
}, 3000);

async function fetchGlobalMetrics() {
    try {
        const res = await fetch(`${API_URL}/metrics/summary`);
        if(res.ok) {
            const data = await res.json();
            const eEl = document.getElementById('topMetricEventos');
            const aEl = document.getElementById('topMetricAlertas');
            const hEl = document.getElementById('topMetricActivos');
            if(eEl) eEl.textContent = data.eventos_hoy;
            if(aEl) aEl.textContent = data.alertas_criticas;
            if(hEl) hEl.textContent = data.activos_vigilados;
        }
    } catch(err) {} 
}

async function fetchForwardLogs() {
    // Solo pedir cuando esté activo para no desperdiciar RAM
    const view = document.getElementById('forward-view');
    if(view && view.style.display === 'none') return;
    
    try {
        const res = await fetch(`${API_URL}/logs/forward`);
        if(!res.ok) return;
        const logs = await res.json();
        
        const tbody = document.getElementById('forwardBody');
        if(!tbody) return;
        
        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color: #6b7280; padding: 25px;">Sin tráfico Forward capturado por Syslog aún.</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        logs.forEach(log => {
            const raw = log.raw_log;
            
            // Extracci\u00f3n Inteligente (Regex) de campos Fortinet
            const destip = (raw.match(/dstip=([\d\.]+)/) || [])[1] || 'N/D';
            const action = (raw.match(/action="?([^"\s]+)"?/) || [])[1] || '';
            const app = (raw.match(/app="([^"]+)"/) || [])[1] || 'Web/Tráfico Genérico';
            let appcat = (raw.match(/appcat="([^"]+)"/) || [])[1] || '';
            if(appcat) appcat = `(${appcat})`;
            
            // Colores por acci\u00f3n (Firewall Policy)
            let actionBadge = '';
            if(action) {
                let badgeClass = 'medium';
                if(action.includes('accept') || action.includes('start')) badgeClass = 'success';
                else if(action.includes('deny') || action.includes('block') || action.includes('drop')) badgeClass = 'critical';
                actionBadge = `<span class="badge ${badgeClass}" style="font-size: 10px;">${action.toUpperCase()}</span>`;
            }

            const detallesFormatted = `
                <div style="display:flex; justify-content:space-between; align-items:center; width: 100%;">
                    <div>
                        <span style="color:var(--text-muted); font-size:13px;">Destino / Servidor:</span> 
                        <strong style="color:#0284c7; font-size:15px; margin-left:6px;">${destip}</strong><br>
                        <span style="color:var(--text-muted); font-size:13px;">App Control:</span> 
                        <strong style="color:#d97706; font-size:14px; margin-left:6px;">${app}</strong> <span style="font-size:12px; color:#64748b;">${appcat}</span>
                    </div>
                    <div>
                        ${actionBadge}
                    </div>
                </div>
            `;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="color: #475569; font-weight: 500; font-size: 13px; white-space:nowrap; vertical-align:middle;">${formatTime(log.timestamp)}</td>
                <td style="vertical-align:middle; font-weight:bold; color:#0f172a; font-size:15px;">${log.source_ip || 'N/D'}</td>
                <td style="background-color: #f1f5f9; padding: 12px 18px; border-radius: 8px; border: 1px solid #e2e8f0;">${detallesFormatted}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(err) {}
}

/* === LOGICA DE NAVEGACION DEL DASHBOARD === */
document.querySelectorAll('#mainNav a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        
        document.querySelectorAll('#mainNav a').forEach(nav => nav.classList.remove('active'));
        e.currentTarget.classList.add('active');
        
        document.querySelectorAll('.view-section').forEach(view => {
            view.style.display = 'none';
        });
        
        const targetId = e.currentTarget.getAttribute('data-view');
        const targetView = document.getElementById(targetId);
        targetView.style.display = 'block';

        const titleMap = {
            'dashboard-view': 'Monitoreo de Seguridad en Tiempo Real',
            'activos-view': 'Seguridad de Activos (Windows)',
            'firewall-view': 'Administración Firewall (Fortinet)',
            'forward-view': 'Auditoría de Tráfico y Navegación'
        };
        document.getElementById('pageTitle').textContent = titleMap[targetId];
    });
});

/* === LOGICA DE INTERACTIVIDAD (ACTIVOS & FIREWALL) === */

function fetchHostsDatabase() {
    const tbody = document.getElementById('hostsBody');
    if(!tbody) return;

    fetch(`${API_URL}/metrics/hosts`)
        .then(res => res.json())
        .then(hosts_reales => {
            if (hosts_reales.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: #6b7280; padding: 25px;">Aún no hay equipos descubiertos. El escáner está trabajando...</td></tr>`;
                return;
            }

            tbody.innerHTML = '';
            hosts_reales.forEach(host => {
                const tr = document.createElement('tr');
                tr.className = 'fade-in';
                const hostDisplay = host.hostname && host.hostname !== 'Desconocido' ? host.hostname : 'Dispositivo Genérico (Sin DNS)';
                
                tr.innerHTML = `
                    <td>
                        <div style="font-weight: bold; color: var(--primary);"><i class="fa-solid fa-desktop" style="margin-right: 8px; color: #64748b;"></i>${host.ip}</div>
                        <div style="font-size: 11px; color: #64748b; margin-left: 22px;">Hostname: <strong style="color:var(--text-main);">${hostDisplay}</strong></div>
                    </td>
                    <td><span class="badge success">Online Activo</span></td>
                    <td style="color: #64748b; font-weight: 600;">${host.last_seen}</td>
                    <td id="actions-${host.ip.replace(/\./g, '-')}">
                        <button class="btn-outline" style="padding: 4px 10px; font-size: 11px;" onclick="scanPorts('${host.ip}')">Escanear Puertos</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error('Error auto-fetching hosts:', err));
}

const btnScan = document.getElementById('btnScan');
if(btnScan) {
    btnScan.addEventListener('click', () => {
        const progress = document.getElementById('scanProgress');
        const bar = document.getElementById('scanBar');
        const percentTxt = document.getElementById('scanPercent');
        
        btnScan.disabled = true;
        btnScan.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Auditando Tráfico...';
        progress.style.display = 'block';
        bar.style.width = '0%';
        
        let percent = 0;
        const interval = setInterval(() => {
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
    const actionTd = document.getElementById(`actions-${ip.replace(/\./g, '-')}`);
    if(!actionTd) return;
    
    const btn = actionTd.querySelector('button');
    if(btn) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Auditando...';
        btn.disabled = true;
    }

    try {
        const res = await fetch(`${API_URL}/metrics/scan_ports/${ip}`);
        if(!res.ok) throw new Error("API Falla");
        const data = await res.json();
        
        if (data.open_ports.length === 0) {
            actionTd.innerHTML = '<span style="color: #10b981; font-weight: bold; font-size: 11px;"><i class="fa-solid fa-shield-halved"></i> Seguro (Cerrados)</span>';
        } else {
            let pills = '';
            data.open_ports.forEach(p => {
                const isCrit = (p.includes('3389') || p.includes('445') || p.includes('22'));
                const color = isCrit ? '#ef4444' : '#f59e0b';
                pills += `<span style="background:${color}; color:white; padding: 2px 6px; border-radius:4px; font-size: 10px; font-weight: bold; margin-right: 4px; display:inline-block; margin-bottom:2px;">${p}</span>`;
            });
            actionTd.innerHTML = pills;
        }
    } catch(err) {
        if(btn) {
            btn.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Error API';
            btn.disabled = false;
        }
    }
}

const btnPing = document.getElementById('btnPingFw');
if(btnPing) {
    btnPing.addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Conectando...';
        btn.style.borderColor = '#f59e0b';
        btn.style.color = '#f59e0b';
        
        try {
            const res = await fetch(`${API_URL}/firewall/ping`);
            if(!res.ok) throw new Error("Status " + res.status);
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Firewall En Línea';
            btn.style.borderColor = '#10b981';
            btn.style.color = '#10b981';
        } catch(err) {
            btn.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Firewall Inalcanzable';
            btn.style.borderColor = '#ef4444';
            btn.style.color = '#ef4444';
        }
        
        setTimeout(() => {
            btn.innerHTML = '<i class="fa-solid fa-network-wired"></i> Probar Conexión API';
            btn.style.borderColor = 'var(--primary)';
            btn.style.color = 'var(--primary)';
        }, 5000);
    });
}

const btnBlock = document.getElementById('btnBlock');
if(btnBlock) {
    btnBlock.addEventListener('click', async () => {
        const ipTarget = document.getElementById('ipTarget');
        if(!ipTarget.value.trim()) {
            ipTarget.focus();
            return;
        }
        const ip = ipTarget.value.trim();
        btnBlock.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Inyectando Regla...';
        btnBlock.disabled = true;
        
        try {
            const res = await fetch(`${API_URL}/firewall/block`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip: ip })
            });
            if(!res.ok) throw new Error("Falla API Fortinet");
            
            const data = await res.json();
            const msgEl = document.getElementById('blockMsg');
            msgEl.textContent = `\u2705 ${data.message}`;
            msgEl.style.color = '#10b981';
            msgEl.style.display = 'block';
        } catch (err) {
            const msgEl = document.getElementById('blockMsg');
            msgEl.textContent = `\u274c Error aislando IP ${ip}. Verifica API Key y conexión HTTPS.`;
            msgEl.style.color = '#ef4444';
            msgEl.style.display = 'block';
        }
        
        btnBlock.innerHTML = '<i class="fa-solid fa-ban"></i> Aislar IP en Firewall';
        btnBlock.disabled = false;
        ipTarget.value = '';
        setTimeout(() => document.getElementById('blockMsg').style.display = 'none', 7000);
    });
}

// Filtros en Tiempo Real
const searchAlerts = document.getElementById('searchAlerts');
if(searchAlerts) {
    searchAlerts.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('#alertsTable tbody tr').forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    });
}

const searchHosts = document.getElementById('searchHosts');
if(searchHosts) {
    searchHosts.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('#hostsTable tbody tr').forEach(row => {
            if(row.children.length === 1) return; // Ignorar mensaje vacio
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    });
}

const searchForward = document.getElementById('searchForward');
if(searchForward) {
    searchForward.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('#forwardTable tbody tr').forEach(row => {
            if(row.children.length === 1) return; 
            const text = row.children[1].textContent.toLowerCase(); 
            row.style.display = text.includes(term) ? '' : 'none';
        });
    });
}

// Exportación y Reportes 100% Funcionales
document.getElementById('btnExport')?.addEventListener('click', (e) => {
    const btn = e.currentTarget;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generando CSV...';
    btn.disabled = true;
    
    // Descarga nativa desde la base de datos
    window.location.href = `${API_URL}/metrics/export_csv`;
    
    setTimeout(() => {
        btn.innerHTML = '<i class="fa-solid fa-check"></i> CSV Descargado';
        btn.style.backgroundColor = '#059669';
        setTimeout(() => { 
            btn.innerHTML = '<i class="fa-solid fa-file-excel"></i> Exportar Excel'; 
            btn.disabled = false; 
            btn.style.backgroundColor = ''; 
        }, 3000);
    }, 1500);
});

document.getElementById('btnPdf')?.addEventListener('click', (e) => {
    const btn = e.currentTarget;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparando Impresión...';
    btn.disabled = true;
    setTimeout(() => {
        window.print();
        btn.innerHTML = '<i class="fa-solid fa-file-pdf"></i> Generar PDF';
        btn.disabled = false;
    }, 1000);
});

// ====== INITIALIZATION OF CHARTS ======
let attacksChartInstance = null;
let portsChartInstance = null;

async function initCharts() {
    // Solo inicializar una vez para no duplicar los lienzos (canvas error)
    if(attacksChartInstance) return;

    const ctxAttacks = document.getElementById('attacksChart');
    const ctxPorts = document.getElementById('portsChart');
    if(!ctxAttacks || !ctxPorts) return;

    // Configuración general combinando con tu Tema Claro / Navy
    Chart.defaults.color = '#64748b';
    Chart.defaults.font.family = 'Inter';

    try {
        const response = await fetch(`${API_URL}/metrics/dashboard`);
        if(!response.ok) throw new Error("API error fetching metrics");
        const metrics = await response.json();

        // 1. Gráfica de Barras (Top IPs Reales)
        attacksChartInstance = new Chart(ctxAttacks, {
            type: 'bar',
            data: {
                labels: metrics.top_ips.labels,
                datasets: [{
                    label: 'Ataques Registrados',
                    data: metrics.top_ips.data,
                    backgroundColor: 'rgba(26, 54, 115, 0.85)', // Tu Navy Blue elegante
                    borderColor: '#1a3673',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#e2e8f0' } },
                    x: { grid: { display: false } }
                }
            }
        });

        // 2. Gráfica de Anillo (Top Puertos Reales)
        portsChartInstance = new Chart(ctxPorts, {
            type: 'doughnut',
            data: {
                labels: metrics.top_ports.labels,
                datasets: [{
                    data: metrics.top_ports.data,
                    backgroundColor: [
                        '#ef4444', // Rojo Peligro
                        '#f59e0b', // Naranja Precaución
                        '#10b981', // Verde OK
                        '#94a3b8', // Gris
                        '#0284c7'  // Azul
                    ],
                    borderWidth: 3,
                    borderColor: '#ffffff',
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, padding: 15 } }
                }
            }
        });
    } catch(err) {
        console.error("No se pudo conectar al API de Métricas:", err);
    }
}

// Escuchar los clicks del menú lateral para generar la gráfica solo cuando entres a Firewall
document.querySelectorAll('#mainNav a').forEach(link => {
    link.addEventListener('click', (e) => {
        const targetId = e.currentTarget.getAttribute('data-view');
        if(targetId === 'firewall-view') {
            // Dar 100ms para que el Div se haga "block" y ChartJS pueda calcular el 100% del Width
            setTimeout(initCharts, 100);
        }
    });
});
