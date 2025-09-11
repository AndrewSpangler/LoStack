# LoStack UI

Web-UI for generating Traefik dynamic configs with the necessary routers, services, and middlewares for Sablier through Traefik's dynamic.yml. It also allows importing / exporting configs in YAML format for easy sharing.

### AI Disclaimer

This project was primarily written by hand.
AI was used to analyze and adjust bootstrap templates, as well as write some auxillary automation (such as fetching js/css from CDNs) that won't pose a security risk.  

AI Was used in 
/scripts folder (scripts to collect css/js from jsdelivr CDN and github)
/static/js/editor_file_types.js (maps common file types to the correct backend mode)


AI was not allowed to touch the following portions:

- Authentication
- ORM Database