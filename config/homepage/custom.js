const processServices = () => {
    const services = document.querySelectorAll(".service");

    // Fix Spacing
    document.querySelectorAll(".services-list").forEach(
        lis => {lis.classList.remove("mt-3");}
    );

    services.forEach(service => {
        const descriptionElem = service.querySelector(".service-description");
        const tagsElem = service.querySelector(".service-tags");
        tagsElem.style.flexDirection = "row-reverse"; 
        tagsElem.style.borderRadius = "5px";
        tagsElem.classList.remove("mr-2");
        tagsElem.classList.remove("gap-2");
        tagsElem.classList.remove("flex");
        tagsElem.classList.remove("flex-row");
        tagsElem.classList.add("px-1");
        

        // Remove default styling from status
        const statusElem = service.querySelector(".docker-status");
        if (statusElem && (statusElem.classList !== null)) {
            statusElem.classList.remove("bg-theme-500/10");
            statusElem.classList.remove("dark:bg-theme-900/50");
            statusElem.classList.remove("px-1.5");
            statusElem.classList.remove("py-0.5");
        }

        const siteElem = service.querySelector(".site-monitor-status");
        if (siteElem && (siteElem.classList !== null)) {
            siteElem.classList.remove("bg-theme-500/10");
            siteElem.classList.remove("dark:bg-theme-900/50");
            siteElem.classList.remove("px-1.5");
            siteElem.classList.remove("py-0.5");

        }
        const nameElem = service.querySelector(".service-name");
        if (nameElem && (nameElem.classList !== null)) {
            nameElem.classList.remove("px-2");
            nameElem.classList.remove("py-2");
            nameElem.classList.add("px-1");
            nameElem.classList.add("py-1");
        }
        
        const cardElem = service.querySelector(".service-card");
        cardElem.classList.remove("mb-2");
        cardElem.classList.add("mb-1");
    
    })

}; 

const classesToRemove = ['bg-theme-500/10', 'dark:bg-theme-900/50'];
function removeClasses(element) {
    if (!element.classList.length) {
        return null;
    }

    classesToRemove.forEach(cls => {
        if (element.classList.contains(cls)) {
            element.classList.remove(cls);
        }
    });
    
}
const callback = function(mutationsList) {
    for (const mutation of mutationsList) {
        if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
            removeClasses(mutation.target);
        } else if (mutation.type === 'childList') {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    removeClasses(node);
                    node.querySelectorAll('*').forEach(removeClasses);
                }
            });
        }
    }
};


var firstRun = true; 
var data = null;

async function applyStyle() {
    if (firstRun) {
        firstRun = false;
        header = document.getElementById("information-widgets");
        header.classList.remove("m-5");
        header.classList.add("m-3.5")        
    }

    processServices();
}   

var updateServices = () => {
    if (document.querySelectorAll(".service").length > 0) {
        let body = document.querySelector("body");
        processServices(body);
    } else {
        console.log("No Services");
    }
}
var checkId = setInterval(updateServices, 500);

applyStyle();