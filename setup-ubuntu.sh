curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-compose docker-ce docker-ce-cli containerd.io

mkdir -p ./appdata
mkdir -p ./appdata/redis-insight
sudo chmod -R 666 ./appdata/redist-insight 

mkdir -p ./media
mkdir -p ./media/audiobooks
mkdir -p ./media/books
mkdir -p ./media/models
mkdir -p ./media/movies
mkdir -p ./media/music
mkdir -p ./media/tv
sudo chmod -R 666 ./media