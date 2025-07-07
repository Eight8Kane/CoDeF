var isDisabledDuringProcessing = false;

function disableScreen() {
    if (!isDisabledDuringProcessing) {
        isDisabledDuringProcessing = true;
        document.getElementById('overlay').style.display = 'block';

        return true;
    }

    return true;
}

function enableScreen() {
    document.getElementById('overlay').style.display = 'none';
    isDisabledDuringProcessing = false;
}

function submit_form_data(url, options) {
    call_api(
        url, {
            method: options.method,
            data: Object.fromEntries(new FormData(options.form)),
            callback: options.callback,
            on_error: options.on_error
        }
    )
}

function submit_multipart_data(formData, method, url, callback) {
    if (disableScreen()) {
        fetch(url, {
            method: method,
            body: formData
        })
            .then((response) => {
                if (response.ok) {
                    return response.json();
                }
                else {
                    throw new Error('Process failed.');
                }
            })
            .then((data) => {
                if (data) {
                    if (callback) {
                        callback(data);
                    }
                    else {
                        window.location.reload();
                    }
                }

                enableScreen();
            })
            .catch((error) => {
                alert(error);
                enableScreen();
            })
    }
}

async function call_api(url, options) {
    if (disableScreen()) {
        response = await fetch(url, {
            method: options.method,
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(options.data),
            redirection: 'manual',
        });

        enableScreen();

        const contentType = response.headers.get('Content-Type');
        var data = null;
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        }

        if (response.ok) {
            if (options.callback) {
                options.callback(data);
            }
            else {
                alert('OK');
            }
        }
        else if (response.status == 401) {
            window.location.href = '/auth/login';
        }
        else if (options.on_error) {
            options.on_error(response.status, data ? data['detail'] : null);
        }
        else {
            alert(`Process failed: [${response.status}] ` + (data && 'detail' in data ? data['detail'] : ''));
        }
    }
}

function validate_form(form) {
    form.find('input[type="text"]').each(function () {
        $(this).val($(this).val().trim());
    })

    if (form[0].checkValidity()) {
        return true;
    }

    form[0].reportValidity();
    return false;
}