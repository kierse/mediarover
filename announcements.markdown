---
layout: default
title: Announcements
desc:
---

{% for post in site.posts %}
<div class="post">
	<div class="date">{{ post.date | date: "%B %d, %Y" }}</div>
	<div class="title">{{post.title}}</div>
	{% if forloop.first %}
		<div class="full">{{post.content}}</div>
		<a href="{{post.url}}">[link]</a>
	{% else %}
		<div class="desc">{{post.desc}}...<a href="{{post.url}}">[link]</a></div>
	{% endif %}
</div>
{% endfor %}
