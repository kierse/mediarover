function edit_filter(element)
{
	// grab form elements and populate with current
	// filter values
	form = document.getElementById('filter_editor');
	inputs = element.getElementsByTagName("span");

	form.series.value = inputs[0].innerHTML;
	form.ignore.value = inputs[3].innerHTML;
	if (inputs[2].innerHTML.toUpperCase() == "YES")
		form.skip.checked = true;
	else
		form.skip.checked = false;

	// update the submit button to say save instead of add
	form.submit.value = "save"

	form.series.focus();
	window.scrollTo(0,0);
}

function multiepisode_allow(element)
{
	form = document.getElementById('multiepisode_editor');
	if (!element.checked)
	{
		form.prefer.checked = false
	}
}

function multiepisode_prefer(element)
{
	form = document.getElementById('multiepisode_editor');
	if (element.checked)
	{
		form.allow.checked = true
	}
}

function edit_source(element)
{
	// grab form elements and populate with current
	// filter values
	form = document.getElementById('source_editor');
	inputs = element.getElementsByTagName("span");

	form.label.value = inputs[0].innerHTML;
	form.url.value = inputs[1].innerHTML;
	form.category.value = inputs[2].innerHTML;
	form.timeout.value = inputs[3].innerHTML;
	form.source.value = inputs[4].innerHTML;

	form.submit.value = "save"

	form.url.focus();
	window.scrollTo(0, 0);
}

function edit_queue(element)
{
	// grab form elements and populate with current
	// filter values
	form = document.getElementById('queue_editor');
	inputs = element.getElementsByTagName("span");

	form.root.value = inputs[0].innerHTML;
	form.api_key.value = inputs[1].innerHTML;
	form.backup_dir.value = inputs[2].innerHTML;
	if(inputs.length == 5)
	{
		form.username.value = inputs[3].innerHTML;
		form.password.value = inputs[4].innerHTML;
	}

	form.submit.value = "save"

	form.api_key.focus();
	window.scrollTo(0, 0);
}
