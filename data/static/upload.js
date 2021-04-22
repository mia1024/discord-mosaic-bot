function resetUpload() {
    $('#image-upload-confirms').css('display', 'none')
    $('label[for="upload"]').css('display', '')
    $('#upload')[0].value=null;
    $('#image-preview').empty()
}

function findScale(){

}

function doUpload(){

}

$('#upload').on('change', e => {
    console.log(e)
    let input = e.target;
    let container = $('#image-preview').empty()
    if (input.files && input.files[0]) {
        let reader = new FileReader();
        console.log(reader)
        reader.onload = () => {
            let wrapper = $('<div class="wrapper"></div>').appendTo(container)
            let img = $(`<img src="${reader.result}" alt="preview">`).appendTo(wrapper)
            img.on('load', () => {
                let width = img[0].naturalWidth;
                let height = img[0].naturalHeight;
                let size = Math.round(input.files[0].size / 1024 / 1024 * 100) / 100;
                wrapper.append(`<p style="text-align: center;width: 100%;margin-top: 1em">Width: ${width}px Height: ${height}px Size: ${size} MiB </p>`);
                $('#image-upload-confirms').css('display', '')
                $('label[for="upload"]').css('display', 'none')
            })
        }
        reader.readAsDataURL(input.files[0]);
    }
})


$(document).foundation()