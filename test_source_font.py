import unittest
from PIL import Image
from source_font import match_source_fonts
from snapshot import render
from balanced_space import fit_translations


class SourceFontTests(unittest.TestCase):
    def test_paragraph_uses_original_line_heights(self):
        rows=[dict(id=1,height=32),dict(id=2,height=34)]
        group=dict(id=1,height=180,members=[1,2])
        matched=match_source_fonts([group],rows)[0]
        self.assertEqual(matched['maximum_font_size'],33)
        self.assertEqual(matched['minimum_font_size'],25)

    def test_large_translation_exceeds_old_cap_in_both_renderers(self):
        row=dict(id=1,x=10,y=10,width=400,height=40,text='Large heading')
        row=match_source_fonts([row],[row])[0]
        for renderer in ['pil','pango']:
            with self.subTest(renderer=renderer):
                _,report=render(Image.new('RGB',(500,100),'white'),[row],{1:'大きな見出し'},renderer=renderer,maximum_font_size=18)
                self.assertTrue(report[0]['shown'])
                self.assertGreaterEqual(report[0]['font_size'],36)

    def test_space_allocation_preserves_source_size(self):
        row=dict(id=1,x=10,y=30,width=100,height=30,text='Settings',minimum_font_size=27,maximum_font_size=30)
        limit=dict(row,y=15,height=100)
        fitted=fit_translations([row],[limit],{1:'設定変更する'},12,18)
        self.assertGreater(fitted[0]['height'],row['height'])
        _,report=render(Image.new('RGB',(200,140),'white'),fitted,{1:'設定変更する'},renderer='pango')
        self.assertTrue(report[0]['shown'])
        self.assertGreaterEqual(report[0]['font_size'],27)

    def test_long_text_does_not_shrink_to_tiny_font(self):
        row=dict(id=1,x=10,y=10,width=70,height=30,text='Settings')
        row=match_source_fonts([row],[row])[0]
        _,report=render(Image.new('RGB',(200,100),'white'),[row],{1:'この領域には収まらない長い翻訳です'},renderer='pango')
        self.assertFalse(report[0]['shown'])

    def test_wrapped_japanese_fits_compact_ui_height(self):
        row=dict(id=1,x=10,y=10,width=100,height=65,text='Change settings',minimum_font_size=27,maximum_font_size=30)
        _,report=render(Image.new('RGB',(200,100),'white'),[row],{1:'設定変更する'},renderer='pango')
        self.assertTrue(report[0]['shown'])
        self.assertEqual(report[0]['font_size'],30)

    def test_allocate_prefers_larger_font_over_smallest_box(self):
        row=dict(id=1,x=10,y=30,width=100,height=30,text='Settings',minimum_font_size=18,maximum_font_size=30)
        limit=dict(row,y=15,height=90)
        fitted=fit_translations([row],[limit],{1:'設定変更する'})
        _,report=render(Image.new('RGB',(200,140),'white'),fitted,{1:'設定変更する'},renderer='pango')
        self.assertTrue(report[0]['shown'])
        self.assertEqual(report[0]['font_size'],30)

    def test_large_font_uses_available_vertical_space(self):
        from balanced_space import budgets
        image=Image.new('RGB',(400,400),'white')
        row=dict(id=1,x=20,y=150,width=100,height=32,text='Settings',minimum_font_size=24,maximum_font_size=32)
        limit=budgets(image,[row])[0]
        self.assertGreater(limit['height'],row['height']+32)
        fitted=fit_translations([row],[limit],{1:'表示設定を変更する'})
        _,report=render(image,fitted,{1:'表示設定を変更する'},renderer='pango')
        self.assertTrue(report[0]['shown'])
        self.assertEqual(report[0]['font_size'],32)

    def test_expanded_budget_stops_before_nearby_text(self):
        from balanced_space import budgets
        image=Image.new('RGB',(400,400),'white')
        row=dict(id=1,x=20,y=150,width=100,height=32,maximum_font_size=32)
        obstacles=[dict(x=20,y=200,width=100,height=30),dict(x=20,y=100,width=100,height=30)]
        limit=budgets(image,[row],obstacles)[0]
        self.assertGreater(limit['y'],130)
        self.assertLess(limit['y']+limit['height'],200)

    def test_horizontal_space_exceeds_old_limit(self):
        from display_space import allocate
        image=Image.new('RGB',(1000,200),'white')
        row=dict(id=1,x=20,y=50,width=100,height=32,maximum_font_size=32)
        allocated,_=allocate(image,[row],[dict(x=600,y=50,width=100,height=32)])
        self.assertGreater(allocated[0]['width'],260)
        self.assertLess(allocated[0]['x']+allocated[0]['width'],600)

    def test_source_pixels_size_small_and_large_text_independently(self):
        from PIL import ImageDraw,ImageFont
        from snapshot import FONT
        image=Image.new('RGB',(600,200),'white')
        draw=ImageDraw.Draw(image)
        rows=[]
        actual=[]
        for index,(y,size) in enumerate([(20,16),(100,40)]):
            font=ImageFont.truetype(FONT,size)
            text='Display settings'
            box=draw.textbbox((20,y),text,font=font,anchor='lt')
            draw.text((20,y),text,font=font,fill='black',anchor='lt')
            rows.append(dict(id=index,x=15,y=y-8,width=400,height=60,text=text))
            actual.append(box[3]-box[1])
        matched=match_source_fonts(rows,rows,image)
        for row,height in zip(matched,actual):
            self.assertLessEqual(abs(row['maximum_font_size']-height),2)
        self.assertGreater(matched[1]['maximum_font_size'],matched[0]['maximum_font_size']*2)

    def test_dark_background_source_measurement(self):
        from PIL import ImageDraw,ImageFont
        from snapshot import FONT
        from source_font import source_ink_height
        image=Image.new('RGB',(400,80),'#202020')
        draw=ImageDraw.Draw(image);font=ImageFont.truetype(FONT,24)
        box=draw.textbbox((20,20),'Settings',font=font,anchor='lt')
        draw.text((20,20),'Settings',font=font,fill='white',anchor='lt')
        row=dict(x=15,y=10,width=250,height=60)
        self.assertLessEqual(abs(source_ink_height(image,row)-(box[3]-box[1])),2)
