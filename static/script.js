function show(e) {
    var c = e.children;
    if (c.length > 0) {
        c[0].style.display = "inline";
    } else {
        var image = e.attributes.oli.value;
        var img = document.createElement("img");
        img.src = image;
        img.className = "popupimage";
        e.appendChild(img);
    }
}

function hide(e) {
    var c = e.children;
    if (c.length > 0) {
        c[0].style.display = "none";
    }
}

function toggle(e) {
    if (e.classList.contains("selectit")) {
        e.classList.remove("selectit");
        e.classList.add("avoidit");
    } else if (e.classList.contains("avoidit")) {
        e.classList.remove("avoidit");
    } else {
        e.classList.add("selectit");
    }
    update_filter(e.parentElement);
}

function update_filter(e) {
    var elems = document.getElementsByClassName("deck");
    var childs = e.children;
    var showit = [];
    var hideit = [];
    var combine = document.getElementById("manaCB").checked;
    for (var c = 0; c < childs.length; ++c) {
        if (childs[c].classList.contains("selectit")) {
            showit.push(childs[c].id)
        } else if (childs[c].classList.contains("avoidit")) {
            hideit.push(childs[c].id)
        }
    }
    for (var idx = 0; idx < elems.length; ++idx) {
        var dc = elems[idx].attributes.dc.value;
        var found = false;
        for (var i = 0; i < hideit.length; ++i) {
            if (dc.indexOf(hideit[i]) > -1) {
                found = true;
                break;
            }
        }
        if (found) {
            elems[idx].classList.add("hideme");
            continue;
        }
        if (combine) {
            found = true;
            for (var i = 0; i < showit.length; ++i) {
                if (dc.indexOf(showit[i]) < 0) {
                    found = false;
                    break;
                }
            }
        } else{
            for (var i = 0; i < showit.length; ++i) {
                if (dc.indexOf(showit[i]) > -1) {
                    found = true;
                    break;
                }
            }
        }
        if (found) {
            elems[idx].classList.remove("hideme");
            continue;
        }
        if (showit.length == 0) {
            elems[idx].classList.remove("hideme");
        } else {
            elems[idx].classList.add("hideme");
        }
    }
}

function add_export(e) {
    var liname = e.id + "-li";
    var li = document.getElementById(liname);
    if (li === null) {
        var ul = document.getElementById("exportlist");
        var li = document.createElement("li");
        li.setAttribute("id", liname);
        var title = document.getElementById(e.id + "-title").innerHTML;
        li.appendChild(document.createTextNode(title + "  "));
        var button = document.createElement("button");
        button.setAttribute("onclick", "remove_export(this.parentElement)");
        button.appendChild(document.createTextNode("X"));
        li.appendChild(button);
        ul.appendChild(li);
    }
}

function remove_export(e) {
    e.parentElement.removeChild(e);
}

function export_deck(e) {
}

function export_list(combine) {
}

function createCookie(name, value, days) {
    if (days) {
        var date = new Date();
        date.setTime(date.getTime()+(days*24*60*60*1000));
        var expires = "; expires="+date.toGMTString();
    }
    else var expires = "";
    document.cookie = name+"="+value+expires+"; path=/";
}

function readCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

function eraseCookie(name) {
    createCookie(name,"",-1);
}

