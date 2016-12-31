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
	var show = [];
	var hide = [];
	var neutral = []
	for (var c = 0; c < childs.length; ++c) {
		if (childs[c].classList.contains("selectit")) {
			show.push(childs[c].id)
		} else if (childs[c].classList.contains("avoidit")) {
			hide.push(childs[c].id)
		} else {
			neutral.push(childs[c].id);
		}
	}
	for (var idx = 0; idx < elems.length; ++idx) {
		elems[idx].style.display = "none";
	}
	for (var idx = 0; idx < elems.length; ++idx) {
		dc = elems[idx].attributes.dc.value;
		for (i = 0; i < neutral.length; ++i) {
			if (dc.indexOf(neutral[i]) > -1) {
				elems[idx].style.display = "";
				break;
			}
		}
	}
	for (var idx = 0; idx < elems.length; ++idx) {
		dc = elems[idx].attributes.dc.value;
		for (i = 0; i < show.length; ++i) {
			if (dc.indexOf(show[i]) > -1) {
				elems[idx].style.display = "";
				break;
			}
		}
	}
	for (var idx = 0; idx < elems.length; ++idx) {
		dc = elems[idx].attributes.dc.value;
		for (i = 0; i < hide.length; ++i) {
			if (dc.indexOf(hide[i]) > -1) {
				elems[idx].style.display = "none";
				break;
			}
		}
	}
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

