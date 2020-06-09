import cv2
import re
from fuzzywuzzy import fuzz
        
class FieldDetection(object):

    def retrieve_fields(self, document):
        fields = ['type',
            'code of issuing state',
            'passport no',
            'surname',
            'given name',
            'nationality',
            'citizenship',
            'date of birth',
            'sex',
            'place of birth',
            'date of issue',
            'authority',
            'date of expiry',
            'country code',
            'code of state',
            'personal no',
            'personal number',
            'issued by']

        doc_words = []
        doc_lines = []
        doc_fields = []
        
        response = {}

        # We extract the words form the api call, appending them in lines and dividing different line on the same horizontal axis
        lenght = 0
        for page in document.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        string = ''
                        start = word.symbols[0].bounding_box.vertices[0]
                        end = word.symbols[-1].bounding_box.vertices[1]

                        if doc_words:
                            if cv2.norm((start.x, start.y), (doc_words[-1]['end'].x, doc_words[-1]['end'].y)) > lenght: 
                                doc_words[-1]['word'] += '\n'
                        lenght = 4*cv2.norm((end.x, end.y), (start.x, start.y))/len(word.symbols)

                        for symbol in word.symbols:
                            string += symbol.text
                            break_type = symbol.property.detected_break.type
                            if break_type == 1: string += ' '
                            if break_type == 2 or break_type == 3 or break_type == 5: string +='\n'

                        doc_words.append({'word':string, 'start':start, 'end':end})

        # From these lines we extrapolate the ones that match a field definition
        line_text = ''
        start = 0
        line_start = doc_words[start]['start']
        for i in range(len(doc_words)):
            line_text += doc_words[i]['word']

            if '\n' in line_text:
                passport = line_text.lower().strip()
                if passport == 'passport' or passport == 'passeport': line_text = ''
                line_split = re.split(r'/|\|', line_text.lower())
                for field in fields:
                    if any(fuzz.ratio(field, line.strip()) > 81 for line in line_split) or field in line_text.lower():
                        line_text = ''
                        if all(cur['field'] != field for cur in doc_fields):
                            doc_fields.append({'field':field, 'start':line_start, 'end':doc_words[i]['end']})
                        elif all(line_start.y > cur['start'].y for cur in doc_fields):
                            for cur in doc_fields: 
                                        if cur['field'] == field: cur['start'] = line_start
                
                if line_text != '':
                    doc_lines.append({'text':line_text.strip(), 'words':doc_words[start:i+1]})

                if i < (len(doc_words)-1):

                    line_text = ''
                    start = i+1
                    line_start = doc_words[start]['start']

        # Now we search the remaining lines to find the closest underneath each field
        for i in range(len(doc_fields)):
            x1 = doc_fields[i]['start'].x
            y1 = doc_fields[i]['start'].y
            best = 150
            result = ''
            dist = 0
            for line in doc_lines:
                x2 = line['words'][0]['start'].x
                y2 = line['words'][0]['start'].y
                x3 = line['words'][-1]['end'].x
                dist = cv2.norm((x1, y1), (x2, y2))
                if dist < best and 0 < y2-y1 < 55 and x3 > x1:
                    
                    if i < len(doc_fields) - 1:

                        field_vertical_distance = abs(doc_fields[i]['end'].y - doc_fields[i+1]['start'].y)
                        # We apply an additional separation for a definition that ends under the next field
                        if field_vertical_distance < 25 and x3 > doc_fields[i+1]['start'].x:
                            for k in range(1, len(line['words'])):
                                next_field = doc_fields[i+1]['start'].x
                                if line['words'][-k]['end'].x > next_field and line['words'][-k-1]['end'].x < next_field:
                                    doc_lines.append({'text':' '.join(line['text'].split()[-k:]), 'words':line['words'][-k:]})
                                    line['words'] = line['words'][:-k]
                                    line['text'] = ' '.join(line['text'].split()[:-k])
                                    break

                    result = line['text']
                    best = dist

            response[doc_fields[i]['field']] = result

        #We check the passport type, it can be max 2 character long and default 'P'
        if 'type' in response:
            if len(response['type']) > 2 or response['type'] == '':
                response['type'] = 'P'

        # Now for extracting the bar code we try to determine the last two lines and merge in the correct order every element found
        lines = []
        for line in doc_lines:
            y = line['words'][0]['start'].y
            if any(abs(y - cur['start']) < 27 for cur in lines):
                for cur in lines:
                    if abs(y - cur['start']) < 27: cur['words'] += line['words']
            else:
                lines.append({'start':y, 'words':line['words']})
        
        barcode = ''
        sorted_lines = sorted(lines, key=lambda k: k['start'])
        for line in sorted_lines[-2:]:
            line['words'] = sorted(line['words'], key=lambda k: k['start'].x)
            for word in line['words']: barcode += word['word'].strip()
        
        response['barcode'] = re.sub("[^0-9A-Z]", "<", barcode)

        #TODO: controllo del codice, unica analisi possibile con la libreria offerta da pyhton, controlla anche lo a capo

        return response