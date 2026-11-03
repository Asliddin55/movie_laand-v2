module.exports = {
  apps: [{
    name: 'movieland-bot',
    script: 'main.py',
    interpreter: 'python3',
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    restart_delay: 3000,
    env: {
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8'
    }
  }]
};
