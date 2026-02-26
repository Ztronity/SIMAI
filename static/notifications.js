let lastCheck = 0;

async function checkNotifications() {
    try {
        const res = await fetch(`/api/notifications/check?since=${lastCheck}`);
        const data = await res.json();

        data.forEach(n => {
            alert(n.message);
            lastCheck = n.timestamp;
        });
    } catch (e) {
        console.error("Erro ao buscar notificações", e);
    }
}

setInterval(checkNotifications, 5000);