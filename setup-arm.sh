https://www.bitdoze.com/install-docker-ubuntu-arm/

sudo apt update
sudo apt-get install ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  jammy stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-compose

mkdir -p ./certs
mkdir -p ./logs
mkdir -p ./traefik-plugins/src/github.com/

mkdir -p ./media
mkdir -p ./media/audiobooks
mkdir -p ./media/books
mkdir -p ./media/comics
mkdir -p ./media/documents
mkdir -p ./media/downloads
mkdir -p ./media/images
mkdir -p ./media/manga
mkdir -p ./media/models
mkdir -p ./media/movies
mkdir -p ./media/music
mkdir -p ./media/podcasts
mkdir -p ./media/recordings
mkdir -p ./media/tv
mkdir -p ./media/www
mkdir -p ./media/youtube
mkdir -p ./media/youtube/general
mkdir -p ./media/youtube/music
mkdir -p ./media/youtube/podcasts
mkdir -p ./media/youtube/temp
mkdir -p ./media/downloads/audiobooks
mkdir -p ./media/downloads/books
mkdir -p ./media/downloads/comics
mkdir -p ./media/downloads/documents
mkdir -p ./media/downloads/general
mkdir -p ./media/downloads/images
mkdir -p ./media/downloads/manga
mkdir -p ./media/downloads/models
mkdir -p ./media/downloads/movies
mkdir -p ./media/downloads/music
mkdir -p ./media/downloads/podcasts
mkdir -p ./media/downloads/recordings
mkdir -p ./media/downloads/temp
mkdir -p ./media/downloads/tv
mkdir -p ./media/downloads/www
mkdir -p ./media/downloads/youtube
mkdir -p ./media/downloads/youtube/general
mkdir -p ./media/downloads/youtube/music
mkdir -p ./media/downloads/youtube/podcasts
mkdir -p ./media/downloads/youtube/temp

sudo chmod -R 666 ./media
sudo systemctl start docker