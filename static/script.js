function show(e) {
    var c = e.children;
    if (c.length > 0) {
        for (var idx = 0; idx < c.length; ++idx) {
            c[idx].style.display = "inline";
        }
    } else {
        var image = e.attributes.oli.value.split(" ");
        for (var idx = 0; idx < image.length; ++idx) {
            var img = document.createElement("img");
            img.src = image[idx];
            img.className = "popupimage";
            e.appendChild(img);
        }
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

function reset_filter(e) {
    var children = e.children;
    for (var idx = 0; idx < children.length; ++idx) {
        var name = children[idx].tagName;
        if (name == "DIV") {
            children[idx].classList.remove("selectit");
            children[idx].classList.remove("avoidit");
        } else if (name == "INPUT") {
            if (children[idx].type == "text") {
                children[idx].value = "";
            } else {
                children[idx].checked = false;
            }
        }
    }

    var elems = document.getElementsByClassName("deck");
    for (var idx = 0; idx < elems.length; ++idx) {
            elems[idx].classList.remove("hideme");
    }
}

function update_filter(e) {
    var elems = document.getElementsByClassName("deck");
    var childs = e.children;
    var showit = [];
    var hideit = [];
    var combine = document.getElementById("manaCB").checked;
    var version = document.getElementById("versionCB").checked;
    var textfilter = document.getElementById("textfilter").value.toLowerCase();
    for (var c = 0; c < childs.length; ++c) {
        if (childs[c].classList.contains("selectit")) {
            showit.push(childs[c].id)
        } else if (childs[c].classList.contains("avoidit")) {
            hideit.push(childs[c].id)
        }
    }
    for (var idx = 0; idx < elems.length; ++idx) {
        if (version && ("old" in elems[idx].attributes)) {
            elems[idx].classList.add("hideme");
            continue;
        }
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
        if (showit.length == 0 && textfilter == "") {
            elems[idx].classList.remove("hideme");
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
        if (showit.length > 0 && !found) {
            elems[idx].classList.add("hideme");
            continue;
        }
        var title = elems[idx].children[0].children[1].textContent.toLowerCase();
        if (title.search(textfilter) > -1) {
            elems[idx].classList.remove("hideme");
            continue;
        }
        var types = elems[idx].children[4].children[0].children;
        var found = false
        for (var tdx = 0; tdx < types.length; ++tdx) {
            var cards = types[tdx].children[1].children[0].children;
            for (var cdx = 0; cdx < cards.length; ++cdx) {
                if (cards[cdx].children[1].textContent.toLowerCase().search(textfilter) > -1) {
                    found = true
                    elems[idx].classList.remove("hideme");
                    continue;
                }
            }
            if (found) {
                continue;
            }
        }
        if (found) {
            continue;
        }
        elems[idx].classList.add("hideme");
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
        var version = document.getElementById(e.id + "-version").innerHTML;
        li.appendChild(document.createTextNode(title + " " + version + "  "));
        var button = document.createElement("button");
        button.setAttribute("onclick", "remove_export(this.parentElement)");
        button.setAttribute("class", "floatbutton");
        button.appendChild(document.createTextNode("X"));
        li.appendChild(button);
        ul.appendChild(li);
    }
}

function remove_export(e) {
    e.parentElement.removeChild(e);
}

function export_deck(e) {
    var deckid = e.id;
    window.open("/export/" + deckid);
}

function export_list(merge) {
    var basic = document.getElementById("exportCB").checked;
    var ul_childs = document.getElementById("exportlist").children;
    var options = "";
    for(var idx = 0; idx < ul_childs.length; ++idx) {
        options += "id=";
        options += ul_childs[idx].id.slice(0, -3);
        options += "&";
    }
    if (options == "") {
        return
    }
    if (basic) {
        options += "nobasic=1&";
    }
    if (merge) {
        options += "merge=1&"
    }
    options = options.slice(0, -1);
    window.open("/exports/?" + options);
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


window.onload = function () {
    document.getElementById("textfilter")
        .addEventListener("keyup", function(event) {
            if (event.keyCode == 13) {
                update_filter(document.getElementById("textfilter").parentElement);
            }
        })
};
