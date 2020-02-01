# Custom crappy html compresser made by me (@mat1)

def compress_html(html):
	output = ''
	inside_tag = False
	line_no = 1
	tag_content = ''
	current_tags = []
	i = 0
	exclude_html_tags = ['meta', '!doctype', 'img', 'link', 'input']
	keep_formatting = ['pre', 'script', 'style', 'code']
	while i < len(html):
		c = html[i]
		if html[i:i+4] == '<!--':
			while html[i:i+3] != '-->':
				i += 1
			i += 3
			c = html[i]
		
		if c == '<':
			inside_tag = True
		elif c == '>':
			if inside_tag:
				inside_tag = False
				tag_name = tag_content.split(' ', 1)[0].lower()
				if tag_name[0] == '/':
					if current_tags[-1] == tag_name[1:]:
						del current_tags[-1]
				else:
					if not tag_name in exclude_html_tags:
						try:
							if current_tags[-1] != 'script':
								current_tags.append(tag_name)
						except IndexError:
							current_tags.append(tag_name)
				# print(tag_content, line_no)
			else:
				pass
			tag_content = ''
		elif inside_tag:
			tag_content += c
		if c == '\n':
			line_no += 1
			try:
				if not current_tags[-1] in keep_formatting:
					i += 1
					while html[i] in '\t ':
						i += 1
					continue
			except IndexError:
				i += 1
				continue
			
		output += c
		i += 1
	return output