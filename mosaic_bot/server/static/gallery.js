async function loadGallery() {
    return await $.ajax('/api/gallery');
}

const search = new JsSearch.Search('id');
search.indexStrategy = new JsSearch.AllSubstringsIndexStrategy();
search.addIndex('name')

function renderGallery(gallery) {
    let main = $('#grid-wrapper').empty();
    main.append('<div class="img-wrapper cell small-12 medium-4 large-3" id="grid-anchor"></div>')
    main.masonry('destroy');
    for (let obj of gallery) {
        let img = $(`<img data-src="${obj.path}" title="${obj.name}" alt="${obj.name}" width="${obj.width}" height="${obj.height}" />`);
        observer.observe(img[0])
        img.on('click', e => openReveal(obj))
        $(`<div class="img-wrapper cell small-12 medium-4 large-3" id="${obj.id}"></div>`).append(img).appendTo(main)

    }
    main.masonry({itemSelector: '.img-wrapper', columnWidth: '#grid-anchor'});
}

loadGallery().then((gallery) => {
        $('#grid-wrapper').masonry({itemSelector: '.img-wrapper'});
        window.fullGallery = gallery;
        window.observer = new IntersectionObserver((entries, ob) => {
            entries.filter(en => en.isIntersecting).map(en => {
                let img = en.target
                img.setAttribute("src", img.getAttribute("data-src"));
                img.removeAttribute("data-src")
                ob.unobserve(img);
            })
        }, {
            rootMargin: '20px',
            threshold: 0.1
        })
        renderGallery(gallery);
        search.addDocuments(gallery);
    }
)

$('#search').on('input', function (e) {
    if (this.hasOwnProperty('timeoutID')) {
        clearTimeout(this.timeoutID)
    }
    this.timeoutID = setTimeout(() => {
        let v = e.target.value;
        if (v === '') {
            $('.img-wrapper').css('display', '')
            $('#grid-wrapper').masonry('destroy').masonry({itemSelector: '.img-wrapper', columnWidth: '#grid-anchor'});

        } else {
            let selected = search.search(v).map(o => o.id);
            $('.img-wrapper').each((i, e) => {
                e.style.display = selected.includes(e.id) ? '' : 'none'
            })
            $('#grid-wrapper').masonry('layout')
        }
    }, 300) // only perform a search after the user isn't typing for 300 ms
})

function openReveal(img) {
    // same imgDetails object as the one sent by the server
    $('#model-image').attr('src', img.path)
    $('#image-properties').empty().append(`
<ul style="text-transform: capitalize">
<h2>${img.name}</h2>
<li>Width: ${img.width}px</li>
<li>Height: ${img.height}px</li>
<li>Uploaded at: ${strftime(new Date(img.time * 1000), "%a %e, %Y")}</li>
</ul>

<h2>Mosaic Commands</h2>
<p>
<pre><code>|show ${img.name}</code></pre>
or
<pre><code>|show ${img.id}</code></pre>
</p>
<p>
Available options: ${
        img.width > 76 ?"" : "<code>with space</code>, "}<code>multiline</code>/<code>irc</code>${img.width > 27 ? "" : ", <code>large</code>"}
</p>

`)
    $('#image-detail').foundation("open")
}

function strftime(date, sFormat) { // https://github.com/thdoan/strftime/blob/master/strftime.js
    if (!(date instanceof Date)) date = new Date();
    var nDay = date.getDay(),
        nDate = date.getDate(),
        nMonth = date.getMonth(),
        nYear = date.getFullYear(),
        nHour = date.getHours(),
        aDays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        aMonths = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
        aDayCount = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334],
        isLeapYear = function () {
            return (nYear % 4 === 0 && nYear % 100 !== 0) || nYear % 400 === 0;
        },
        getThursday = function () {
            var target = new Date(date);
            target.setDate(nDate - ((nDay + 6) % 7) + 3);
            return target;
        },
        zeroPad = function (nNum, nPad) {
            return ((Math.pow(10, nPad) + nNum) + '').slice(1);
        };
    return sFormat.replace(/%[a-z]/gi, function (sMatch) {
        return (({
            '%a': aDays[nDay].slice(0, 3),
            '%A': aDays[nDay],
            '%b': aMonths[nMonth].slice(0, 3),
            '%B': aMonths[nMonth],
            '%c': date.toUTCString(),
            '%C': Math.floor(nYear / 100),
            '%d': zeroPad(nDate, 2),
            '%e': nDate,
            '%F': date.toISOString().slice(0, 10),
            '%G': getThursday().getFullYear(),
            '%g': (getThursday().getFullYear() + '').slice(2),
            '%H': zeroPad(nHour, 2),
            '%I': zeroPad((nHour + 11) % 12 + 1, 2),
            '%j': zeroPad(aDayCount[nMonth] + nDate + ((nMonth > 1 && isLeapYear()) ? 1 : 0), 3),
            '%k': nHour,
            '%l': (nHour + 11) % 12 + 1,
            '%m': zeroPad(nMonth + 1, 2),
            '%n': nMonth + 1,
            '%M': zeroPad(date.getMinutes(), 2),
            '%p': (nHour < 12) ? 'AM' : 'PM',
            '%P': (nHour < 12) ? 'am' : 'pm',
            '%s': Math.round(date.getTime() / 1000),
            '%S': zeroPad(date.getSeconds(), 2),
            '%u': nDay || 7,
            '%V': (function () {
                var target = getThursday(),
                    n1stThu = target.valueOf();
                target.setMonth(0, 1);
                var nJan1 = target.getDay();
                if (nJan1 !== 4) target.setMonth(0, 1 + ((4 - nJan1) + 7) % 7);
                return zeroPad(1 + Math.ceil((n1stThu - target) / 604800000), 2);
            })(),
            '%w': nDay,
            '%x': date.toLocaleDateString(),
            '%X': date.toLocaleTimeString(),
            '%y': (nYear + '').slice(2),
            '%Y': nYear,
            '%z': date.toTimeString().replace(/.+GMT([+-]\d+).+/, '$1'),
            '%Z': date.toTimeString().replace(/.+\((.+?)\)$/, '$1')
        }[sMatch] || '') + '') || sMatch;
    });
}

$(document).foundation();
