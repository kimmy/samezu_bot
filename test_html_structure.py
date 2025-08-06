#!/usr/bin/env python3
"""
Test script to verify slot detection using the provided HTML structure
This file contains the exact HTML structure with an available slot for testing
"""

import asyncio
import logging
from playwright.async_api import async_playwright

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# The HTML structure provided by the user - contains an available slot
TEST_HTML = """
<table id="TBL" class="time--table" aria-describedby="TBLsummary"> 
    <tbody>
        <tr id="height_head">
            <th class="time--table time--th backgroud bordernone main_color time--table--nowrap" rowspan="2">施設名</th>
            <th class="time--table time--th backgroud bordernone main_color time--table--nowrap" rowspan="2">予約枠名</th>
            <td class="time--table time--th bordernone" colspan="14">
                <div class="calender_pager">
                    <ul class="calender_pager_left">
                        <li><input type="button" value="＜3か月前" disabled="" aria-label="3か月前のカレンダーページへ" class="button"></li>
                        <li><input type="button" value="＜1か月前" disabled="" aria-label="1か月前のカレンダーページへ" class="button"></li>
                        <li><input type="button" value="＜2週前" title="予約可能な週へ戻る" aria-label="2週前のカレンダーページへ" onclick="nextDate('previous');" class="button"></li>
                    </ul>
                    2025年
                    <ul class="calender_pager_right">
                        <li><input type="button" value="3か月後＞" disabled="" aria-label="3か月後のカレンダーページへ" class="button"></li>
                        <li><input type="button" value="1か月後＞" title="1か月後に進む" aria-label="1か月後のカレンダーページへ" onclick="nextDate('oneMonthLater');" class="button"></li>
                        <li><input type="button" value="2週後＞" title="予約可能な週へ進む" aria-label="2週後のカレンダーページへ" onclick="nextDate('next');" class="button"></li>
                    </ul>
                </div>
            </td>
        </tr>
        <tr id="height_headday">
            <td class="time--table time--th--date bordernone">
                <span style="color:#E12800 ">08/17<br>(Sun)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/18<br>(Mon)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/19<br>(Tue)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/20<br>(Wed)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/21<br>(Thu)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/22<br>(Fri)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#0F4DFF ">08/23<br>(Sat)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#E12800 ">08/24<br>(Sun)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/25<br>(Mon)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/26<br>(Tue)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/27<br>(Wed)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/28<br>(Thu)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#000000 ">08/29<br>(Fri)</span>
            </td>
            <td class="time--table time--th--date bordernone">
                <span style="color:#0F4DFF ">08/30<br>(Sat)</span>
            </td>
        </tr>
        <tr id="height_auto_29の国･地域以外の方で、住民票のない方" style="height: 0px;">
            <th class="time--table time--th backgroud bordernone" rowspan="1"> 
                <a href="facilityDetail_initDisplay?facilityCd=FC00078&amp;tempSeq=445" target="_blank" title="施設情報画面を開きます。"> 
                    鮫洲試験場
                </a>
            </th>
            <th class="time--table time--th backgroud bordernone main_color">
                29の国･地域以外の方で、住民票のない方
            </th>
            <td class="time--table time--th--date bordernone time--cell--tri none">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="時間外" focusable="false">
                    <defs><style>.tri-cls-1,.tri-cls-2{fill:none;}.tri-cls-1{stroke:#000000;stroke-miterlimit:10;stroke-width:2px;}</style></defs>
                    <line class="tri-cls-1" x1="4" y1="10" x2="16" y2="10"></line>
                    <rect class="tri-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone time--cell--tri none">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="時間外" focusable="false">
                    <defs><style>.tri-cls-1,.tri-cls-2{fill:none;}.tri-cls-1{stroke:#000000;stroke-miterlimit:10;stroke-width:2px;}</style></defs>
                    <line class="tri-cls-1" x1="4" y1="10" x2="16" y2="10"></line>
                    <rect class="tri-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone time--cell--tri none">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="時間外" focusable="false">
                    <defs><style>.tri-cls-1,.tri-cls-2{fill:none;}.tri-cls-1{stroke:#000000;stroke-miterlimit:10;stroke-width:2px;}</style></defs>
                    <line class="tri-cls-1" x1="4" y1="10" x2="16" y2="10"></line>
                    <rect class="tri-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone time--cell--tri none">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="時間外" focusable="false">
                    <defs><style>.tri-cls-1,.tri-cls-2{fill:none;}.tri-cls-1{stroke:#000000;stroke-miterlimit:10;stroke-width:2px;}</style></defs>
                    <line class="tri-cls-1" x1="4" y1="10" x2="16" y2="10"></line>
                    <rect class="tri-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone tdSelect enable" onclick="selectDate(&quot;FC00078&quot;, &quot;20250821&quot;, &quot;1&quot;, this);">
                <a class="enable nooutline" href="#" onblur="commonUtil.changeBackColor(this,'parent')" onfocus="commonUtil.changeBackColor(this,'parent')">
                    <span class="sr-only">29の国･地域以外の方で、住民票のない方は2025年08月21日 </span>
                    <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg" viewBox="0 1.5 20 20" role="img" aria-label="予約可能" focusable="false">
                        <defs><style>.ok-cls-1,.ok-cls-2{fill:none;}.ok-cls-1{stroke:#008A2B;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                        <circle class="ok-cls-1" cx="10" cy="10" r="7"></circle>
                        <rect class="ok-cls-2" width="20" height="20"></rect>
                    </svg>
                </a>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone time--cell--tri none">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="時間外" focusable="false">
                    <defs><style>.tri-cls-1,.tri-cls-2{fill:none;}.tri-cls-1{stroke:#000000;stroke-miterlimit:10;stroke-width:2px;}</style></defs>
                    <line class="tri-cls-1" x1="4" y1="10" x2="16" y2="10"></line>
                    <rect class="tri-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone time--cell--tri none">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="時間外" focusable="false">
                    <defs><style>.tri-cls-1,.tri-cls-2{fill:none;}.tri-cls-1{stroke:#000000;stroke-miterlimit:10;stroke-width:2px;}</style></defs>
                    <line class="tri-cls-1" x1="4" y1="10" x2="16" y2="10"></line>
                    <rect class="tri-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone disable">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="空き無" focusable="false">
                    <defs><style>.ng-cls-1,.ng-cls-2{fill:none;}.ng-cls-1{stroke:#ED1212;stroke-miterlimit:10;stroke-width:3px;}</style></defs>
                    <line class="ng-cls-1" x1="2.4" y1="2.4" x2="17.6" y2="17.6"></line>
                    <line class="ng-cls-1" x1="17.6" y1="2.4" x2="2.4" y2="17.6"></line>
                    <rect class="ng-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
            <td class="time--table time--th--date bordernone time--cell--tri none">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 2 20 20" role="img" aria-label="時間外" focusable="false">
                    <defs><style>.tri-cls-1,.tri-cls-2{fill:none;}.tri-cls-1{stroke:#000000;stroke-miterlimit:10;stroke-width:2px;}</style></defs>
                    <line class="tri-cls-1" x1="4" y1="10" x2="16" y2="10"></line>
                    <rect class="tri-cls-2" width="20" height="20"></rect>
                </svg>
            </td>
        </tr>
    </tbody>
</table>
"""

async def test_html_structure():
    """Test the slot detection logic using the provided HTML structure"""
    print("🔍 Testing slot detection with provided HTML structure...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Set the HTML content
            await page.set_content(TEST_HTML)
            print("✅ HTML content set successfully")
            
            # Test the current logic from reservation_checker.py
            available_slots = []
            
            # First, get the date headers from the second row
            date_headers = []
            rows = await page.query_selector_all('tr')
            if len(rows) > 1:
                date_row = rows[1]  # The row with dates
                date_header_cells = await date_row.query_selector_all('td')
                for cell in date_header_cells:
                    date_text = await cell.text_content()
                    if date_text and date_text.strip():
                        clean_date = ' '.join(date_text.strip().split())
                        if clean_date and len(clean_date) > 2:
                            date_headers.append(clean_date)
            
            print(f"📅 Date headers found: {date_headers}")
            
            # Find all rows for target facilities
            for row_idx, row in enumerate(rows):
                print(f"\n🔍 Checking row {row_idx + 1}")
                
                # Get the facility name from the first cell (could be th or td)
                facility_cell = await row.query_selector('th:first-child, td:first-child')
                if not facility_cell:
                    print(f"   ❌ No facility cell found")
                    continue

                facility_text = await facility_cell.text_content()
                if not facility_text:
                    print(f"   ❌ No facility text found")
                    continue

                print(f"   📍 Facility text: '{facility_text.strip()}'")

                # Check if this row is for any of our target facilities
                target_facility = None
                for facility in ["府中試験場", "鮫洲試験場"]:
                    if facility in facility_text:
                        target_facility = facility
                        break

                if not target_facility:
                    print(f"   ❌ Not a target facility")
                    continue

                print(f"   ✅ Target facility found: {target_facility}")

                # Get applicant type from second cell (could be th or td)
                applicant_cell = await row.query_selector('th:nth-child(2), td:nth-child(2)')
                if not applicant_cell:
                    print(f"   ❌ No applicant cell found")
                    continue

                applicant_type = await applicant_cell.text_content()
                applicant_type = applicant_type.strip() if applicant_type else "Unknown"
                print(f"   👤 Applicant type: '{applicant_type}'")

                # Check all date cells for availability (exclude first two cells)
                date_cells = await row.query_selector_all('td:not(:first-child):not(:nth-child(2))')
                print(f"   📅 Found {len(date_cells)} date cells")

                for i, cell in enumerate(date_cells):
                    # Use the date from our pre-collected headers
                    if i < len(date_headers):
                        date_text = date_headers[i]
                    else:
                        date_text = f"Unknown date {i + 1}"

                    print(f"\n      🔍 Checking date: {date_text}")
                    print(f"         Facility: {target_facility}")
                    print(f"         Applicant: {applicant_type}")

                    # Test the current logic: check for any SVG with aria-label="予約可能"
                    svg = await cell.query_selector('svg')
                    if svg:
                        aria_label = await svg.get_attribute('aria-label')
                        print(f"         SVG aria-label: '{aria_label}'")
                        
                        if aria_label == "予約可能":
                            available_slots.append({
                                'date': date_text,
                                'facility': target_facility,
                                'applicant_type': applicant_type
                            })
                            print(f"         ✅ FOUND AVAILABLE SLOT!")
                        elif aria_label == "空き無":
                            print(f"         ❌ No availability")
                        elif aria_label == "時間外":
                            print(f"         ⏰ Outside hours")
                    else:
                        print(f"         No SVG found in cell")
                        
                        # Let's also check what's actually in the cell
                        cell_html = await cell.inner_html()
                        print(f"         Cell HTML: {cell_html[:200]}...")
            
            print(f"\n📊 RESULTS:")
            if available_slots:
                print(f"✅ Found {len(available_slots)} available slots:")
                for slot in available_slots:
                    print(f"   📅 {slot['date']} - {slot['facility']} - {slot['applicant_type']}")
            else:
                print("❌ No available slots found")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_html_structure()) 
