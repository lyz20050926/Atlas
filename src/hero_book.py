"""The Atlas knowledge observatory: paper, light, and a living intelligence lens.

Each paper surface has its own lighting, rather than mirroring one flat page.
Motion is supplied by the host stylesheet so pause and reduced-motion controls
can stop the entire scene without JavaScript or an external rendering library.
"""


def hero_book_scene_svg() -> str:
    """Return a self-contained holographic observatory grounded by a physical book."""
    paper_edges = "".join(
        '<path d="'
        f'M{106 - t:.2f} {356 + 17 * t:.2f} '
        f'C184 {342 + 18 * t:.2f} 279 {376 + 19 * t:.2f} '
        f'{352 - 3 * t:.2f} {418 + 13 * t:.2f} '
        f'M{358 + 2 * t:.2f} {418 + 13 * t:.2f} '
        f'C451 {366 + 19 * t:.2f} 548 {322 + 16 * t:.2f} '
        f'647 {338 + 13 * t:.2f}" '
        f'stroke="{"#86a9d3" if index % 3 == 0 else "#ffffff"}" '
        f'stroke-width="{0.6 if index % 3 == 0 else 0.85}" '
        f'opacity="{0.52 if index % 3 == 0 else 0.82}"/>'
        for index, t in enumerate(index / 14 for index in range(15))
    )
    left_ink = "".join(
        f'<path d="M{160 - i * 2.1:.1f} {272 + i * 10.2:.1f} '
        f'C202 {264 + i * 10.2:.1f} {252 if i in (2, 6) else 279} '
        f'{280 + i * 10.0:.1f} {287 if i in (2, 6) else 320} '
        f'{299 + i * 10.0:.1f}"/>'
        for i in range(7)
    )
    nodes = "".join(
        f'<g transform="translate({x} {y})">'
        f'<circle r="{radius + 5}" fill="#d9eaff" opacity=".5"/>'
        f'<circle class="atlas-book-node" r="{radius}" '
        f'fill="#ffffff" stroke="#3b86e8" stroke-width="1.5" '
        f'style="animation-delay:-{i * .61:.2f}s"/>'
        '</g>'
        for i, (x, y, radius) in enumerate(
            ((348, 145, 3.5), (389, 103, 3), (414, 165, 5.5),
             (453, 123, 3.5), (488, 169, 3), (445, 221, 3),
             (380, 224, 2.5), (333, 191, 2.5))
        )
    )
    return """
      <svg class="atlas-book-scene" viewBox="0 0 720 500" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="atlasBookCover" x1="190" y1="295" x2="440" y2="472" gradientUnits="userSpaceOnUse">
            <stop stop-color="#4a94ee"/><stop offset=".48" stop-color="#1f6acf"/>
            <stop offset=".85" stop-color="#124b9d"/><stop offset="1" stop-color="#0b3574"/>
          </linearGradient>
          <linearGradient id="atlasBookCoverRim" x1="93" y1="360" x2="652" y2="397" gradientUnits="userSpaceOnUse">
            <stop stop-color="#5ba2f2"/><stop offset=".44" stop-color="#286dc5"/>
            <stop offset=".53" stop-color="#83b6f3"/><stop offset="1" stop-color="#2568be"/>
          </linearGradient>
          <linearGradient id="atlasBookPaperBlock" x1="0" y1="0" x2="0" y2="1">
            <stop stop-color="#fff"/><stop offset=".3" stop-color="#eef5ff"/>
            <stop offset=".72" stop-color="#d9e7f7"/><stop offset="1" stop-color="#9cb9dd"/>
          </linearGradient>
          <linearGradient id="atlasBookLeftPaper" x1="137" y1="267" x2="359" y2="326" gradientUnits="userSpaceOnUse">
            <stop stop-color="#f9fcff"/><stop offset=".48" stop-color="#fff"/>
            <stop offset=".8" stop-color="#f0f5fd"/><stop offset=".94" stop-color="#cfdef1"/>
            <stop offset="1" stop-color="#97b5db"/>
          </linearGradient>
          <linearGradient id="atlasBookRightPaper" x1="363" y1="327" x2="615" y2="281" gradientUnits="userSpaceOnUse">
            <stop stop-color="#a4c0e2"/><stop offset=".12" stop-color="#dce9f8"/>
            <stop offset=".44" stop-color="#f5f9ff"/><stop offset=".88" stop-color="#fff"/>
            <stop offset="1" stop-color="#eaf2fd"/>
          </linearGradient>
          <linearGradient id="atlasBookRaisedPaper" x1="372" y1="307" x2="608" y2="248" gradientUnits="userSpaceOnUse">
            <stop stop-color="#b4cbea"/><stop offset=".16" stop-color="#e7f0fc"/>
            <stop offset=".46" stop-color="#fff"/><stop offset=".9" stop-color="#fff"/>
            <stop offset="1" stop-color="#e4effc"/>
          </linearGradient>
          <linearGradient id="atlasBookLeafUnder" x1="488" y1="297" x2="475" y2="336" gradientUnits="userSpaceOnUse">
            <stop stop-color="#729acf" stop-opacity=".33"/><stop offset="1" stop-color="#acc9ed" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="atlasBookFold" x1="347" y1="345" x2="378" y2="348" gradientUnits="userSpaceOnUse">
            <stop stop-color="#729acb" stop-opacity="0"/><stop offset=".48" stop-color="#3465a4" stop-opacity=".4"/>
            <stop offset=".72" stop-color="#fff" stop-opacity=".75"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
          </linearGradient>
          <linearGradient id="atlasBookRibbon" x1="360" y1="413" x2="388" y2="465" gradientUnits="userSpaceOnUse">
            <stop stop-color="#82bbff"/><stop offset=".5" stop-color="#3f88e9"/><stop offset="1" stop-color="#1958b9"/>
          </linearGradient>
          <linearGradient id="atlasLinkGradient" x1="345" y1="231" x2="484" y2="75" gradientUnits="userSpaceOnUse">
            <stop stop-color="#508be1" stop-opacity=".67"/><stop offset="1" stop-color="#92bdf2" stop-opacity=".48"/>
          </linearGradient>
          <linearGradient id="atlasBookBeam" x1="0" y1="1" x2="0" y2="0">
            <stop stop-color="#83b9fb" stop-opacity=".12"/><stop offset="1" stop-color="#a8ceff" stop-opacity="0"/>
          </linearGradient>
          <radialGradient id="atlasBookAura">
            <stop stop-color="#99c7ff" stop-opacity=".45"/><stop offset=".58" stop-color="#c5dfff" stop-opacity=".18"/>
            <stop offset="1" stop-color="#eaf4ff" stop-opacity="0"/>
          </radialGradient>
          <radialGradient id="atlasLensGlass" cx=".3" cy=".23" r=".86">
            <stop stop-color="#fff" stop-opacity=".94"/>
            <stop offset=".37" stop-color="#f0f8ff" stop-opacity=".62"/>
            <stop offset=".69" stop-color="#cde4ff" stop-opacity=".46"/>
            <stop offset=".92" stop-color="#7eb7f7" stop-opacity=".42"/>
            <stop offset="1" stop-color="#4e95e9" stop-opacity=".12"/>
          </radialGradient>
          <radialGradient id="atlasLensLight" cx=".36" cy=".29" r=".7">
            <stop stop-color="#fff" stop-opacity=".94"/>
            <stop offset=".48" stop-color="#b0d6ff" stop-opacity=".28"/>
            <stop offset="1" stop-color="#4799f1" stop-opacity="0"/>
          </radialGradient>
          <linearGradient id="atlasLensRim" x1="331" y1="65" x2="481" y2="263" gradientUnits="userSpaceOnUse">
            <stop stop-color="#fff"/><stop offset=".38" stop-color="#adcefa" stop-opacity=".5"/>
            <stop offset=".72" stop-color="#3585e4" stop-opacity=".52"/>
            <stop offset="1" stop-color="#d0e7ff" stop-opacity=".6"/>
          </linearGradient>
          <linearGradient id="atlasOrbitLight" x1="230" y1="241" x2="600" y2="110" gradientUnits="userSpaceOnUse">
            <stop stop-color="#7ab8fb" stop-opacity=".08"/><stop offset=".38" stop-color="#3787e9" stop-opacity=".75"/>
            <stop offset=".72" stop-color="#64a9f6" stop-opacity=".5"/><stop offset="1" stop-color="#c5e0ff" stop-opacity=".15"/>
          </linearGradient>
          <linearGradient id="atlasProjection" x1="370" y1="340" x2="410" y2="216" gradientUnits="userSpaceOnUse">
            <stop stop-color="#388bea" stop-opacity=".02"/><stop offset=".48" stop-color="#91c6ff" stop-opacity=".19"/>
            <stop offset="1" stop-color="#d8edff" stop-opacity=".03"/>
          </linearGradient>
          <linearGradient id="atlasGlassPage" x1="0" y1="0" x2="1" y2="1">
            <stop stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#daedff" stop-opacity=".3"/>
          </linearGradient>
          <filter id="atlasHologramGlow" x="-75%" y="-75%" width="250%" height="250%">
            <feGaussianBlur stdDeviation="3.5"/>
          </filter>
          <clipPath id="atlasLensClip"><circle cx="414" cy="165" r="105"/></clipPath>
          <filter id="atlasBookGroundShadow" x="-30%" y="-180%" width="160%" height="460%">
            <feGaussianBlur stdDeviation="13"/>
          </filter>
          <filter id="atlasBookContactShadow" x="-30%" y="-100%" width="160%" height="300%">
            <feGaussianBlur stdDeviation="4"/>
          </filter>
          <pattern id="atlasBookCloth" width="4" height="4" patternUnits="userSpaceOnUse">
            <path d="M0 0H4M0 0V4" fill="none" stroke="#fff" stroke-width=".35" opacity=".13"/>
          </pattern>
          <clipPath id="atlasBookLeftClip">
            <path d="M143 239 C220 216 300 237 367 290 C372 335 363 378 353 419 C279 376 182 341 106 356Z"/>
          </clipPath>
        </defs>

        <ellipse class="atlas-book-aura" cx="396" cy="246" rx="302" ry="228" fill="url(#atlasBookAura)"/>
        <g class="atlas-observatory-guides" fill="none" stroke="#b6d4f7" stroke-width=".8">
          <path d="M238 94 A212 185 -15 0 1 581 100" opacity=".38"/>
          <path d="M192 216 A240 220 -15 0 1 477 25" stroke-dasharray="1 9" opacity=".53"/>
          <ellipse cx="376" cy="444" rx="248" ry="24" opacity=".38"/>
          <path d="M130 444 H171 M581 444 H621 M376 417 V410 M376 473 V478" opacity=".5"/>
          <path d="M242 90 h9 m-4.5 -4.5 v9 M572 280 h8 m-4 -4 v8 M188 248 h6 m-3 -3 v6" opacity=".55"/>
        </g>

        <path class="atlas-book-signal" d="M345 355 Q328 290 326 231 Q403 202 490 235 Q433 297 390 358Z" fill="url(#atlasProjection)"/>
        <g class="atlas-book-projection" fill="none" stroke="#66aaf3" stroke-width=".75">
          <path d="M352 360 Q327 301 327 236 M386 358 Q458 293 491 237" opacity=".2"/>
          <path class="atlas-book-flow" d="M366 357 Q347 291 380 224 L414 165"/>
          <path class="atlas-book-flow is-slow" d="M380 356 Q433 279 445 221 L488 169"/>
        </g>

        <g class="atlas-book-network">
          <g class="atlas-book-orbit-back" fill="none">
            <ellipse cx="414" cy="165" rx="194" ry="64" transform="rotate(-19 414 165)" stroke="#bad7f9" stroke-width=".9" opacity=".59"/>
            <ellipse cx="414" cy="165" rx="133" ry="102" transform="rotate(-40 414 165)" stroke="#cadff9" stroke-width=".75" stroke-dasharray="2 7" opacity=".6"/>
          </g>

          <g class="atlas-book-core">
            <circle cx="414" cy="165" r="106" fill="url(#atlasLensGlass)" stroke="url(#atlasLensRim)" stroke-width="1.3"/>
            <circle cx="414" cy="165" r="101" fill="none" stroke="#fff" stroke-width=".8" opacity=".4"/>
            <g clip-path="url(#atlasLensClip)">
              <ellipse cx="381" cy="137" rx="119" ry="95" fill="url(#atlasLensLight)"/>
              <g fill="none" stroke="#88b8ef" stroke-width=".65" opacity=".29">
                <ellipse cx="414" cy="165" rx="51" ry="107" transform="rotate(29 414 165)"/>
                <ellipse cx="414" cy="165" rx="86" ry="106" transform="rotate(29 414 165)"/>
                <ellipse cx="414" cy="165" rx="107" ry="36" transform="rotate(-17 414 165)"/>
                <path d="M313 124 Q404 102 504 100 M322 219 Q419 238 509 194"/>
              </g>
              <path d="M334 97 Q374 64 420 66" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".77"/>
              <path d="M326 115 Q322 123 320 131" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".65"/>
              <path d="M359 253 Q435 285 496 229" fill="none" stroke="#5797e9" stroke-width="3" opacity=".18"/>
              <g class="atlas-book-core-lattice" fill="none" stroke="#649ded" stroke-width="1.05">
                <path d="M348 145 389 103 453 123 488 169 445 221 380 224 333 191 348 145 414 165 389 103 M333 191 414 165 453 123 M380 224 414 165 488 169 M414 165 445 221" opacity=".6"/>
                <path d="M348 145 453 123 M389 103 445 221 M333 191 488 169" stroke-dasharray="2 5" opacity=".24"/>
              </g>
              <circle class="atlas-book-signal" cx="414" cy="165" r="23" fill="#6eafff" opacity=".22" filter="url(#atlasHologramGlow)"/>
              <path d="M414 144 435 165 414 186 393 165Z" fill="none" stroke="#fff" stroke-width="1.8" opacity=".75"/>
              __NODES__
            </g>
          </g>

          <g class="atlas-book-orbit" fill="none">
            <path d="M230 232 C258 277 425 237 543 177 C588 153 606 130 598 116" stroke="#fff" stroke-width="3" opacity=".75"/>
            <path d="M230 232 C258 277 425 237 543 177 C588 153 606 130 598 116" stroke="url(#atlasOrbitLight)" stroke-width="1.4"/>
            <path class="atlas-book-flow" d="M232 232 C263 269 423 235 543 176" opacity=".68"/>
            <circle cx="542" cy="177" r="8" fill="#7ab6ff" opacity=".16"/>
            <circle cx="542" cy="177" r="3" fill="#fff" stroke="#3e8eed" stroke-width="1.5"/>
            <circle cx="273" cy="250" r="2.1" fill="#fff" stroke="#81b8f6" stroke-width="1"/>
          </g>
        </g>

        <g class="atlas-book-memory" transform="translate(557 248) rotate(-11)" opacity=".77">
          <path d="M4 7 50 0 50 54 4 61Z" fill="url(#atlasGlassPage)" stroke="#b6d7fc" stroke-width=".8"/>
          <path d="M11 15 42 10 M11 21 35 17 M11 38 29 34 M11 44 37 39" fill="none" stroke="#92b9e8" stroke-width="1" opacity=".58"/>
          <path d="M34 29 37 32 43 24" fill="none" stroke="#4f98eb" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </g>
        <g fill="#69a7ee" opacity=".48">
          <circle cx="236" cy="139" r="1.5"/><circle cx="534" cy="46" r="1.6"/>
          <circle cx="612" cy="234" r="1.3"/><circle cx="213" cy="292" r="1.1"/>
          <circle cx="306" cy="51" r="1.3"/>
        </g>

        <ellipse class="atlas-book-ground" cx="369" cy="453" rx="219" ry="15" fill="#3a6ca5" opacity=".14" filter="url(#atlasBookGroundShadow)"/>
        <ellipse cx="359" cy="451" rx="84" ry="5" fill="#2a5e9e" opacity=".1" filter="url(#atlasBookContactShadow)"/>

        <g transform="translate(55 80) scale(.84)"><g class="atlas-book-pages">
          <g class="atlas-book-cover">
            <path d="M137 235 C224 212 304 241 370 290 C454 215 539 193 619 211 L665 349 665 358 C555 338 454 394 365 446 Q352 453 340 445 C249 391 163 369 87 385 L90 374Z" fill="url(#atlasBookCover)" stroke="#235fa9" stroke-width=".8"/>
            <path d="M137 235 C224 212 304 241 370 290 C454 215 539 193 619 211 L665 349 665 358 C555 338 454 394 365 446 Q352 453 340 445 C249 391 163 369 87 385 L90 374Z" fill="url(#atlasBookCloth)"/>
            <path d="M90 374 C172 354 257 383 343 436 Q353 443 363 437 C460 384 549 329 665 349 L665 354 C554 333 457 391 365 443 Q353 450 341 442 C251 389 170 361 88 381Z" fill="url(#atlasBookCoverRim)"/>
            <path d="M97 374 C174 358 264 391 342 437 Q353 444 364 437 C456 385 559 333 660 350" fill="none" stroke="#97c5ff" stroke-width=".9" opacity=".68"/>
            <path d="M340 436 Q353 444 366 436 L365 446 Q352 453 340 445Z" fill="#123e7e" opacity=".8"/>
          </g>

          <path d="M106 356 C182 341 279 376 352 418 L358 418 C451 366 548 322 647 338 L646 351 C552 337 452 384 360 432 Q353 437 347 432 C275 395 182 359 105 373Z" fill="url(#atlasBookPaperBlock)" stroke="#c0d2e8" stroke-width=".65"/>
          <g class="atlas-book-page-edges" fill="none">__PAPER_EDGES__</g>

          <path class="atlas-book-page atlas-book-page-left" d="M143 239 C220 216 300 237 367 290 C372 335 363 378 353 419 C279 376 182 341 106 356Z" fill="url(#atlasBookLeftPaper)" stroke="#cadcf1" stroke-width=".85"/>
          <path class="atlas-book-page atlas-book-page-right" d="M367 290 C448 216 527 202 612 218 L647 338 C548 322 451 367 356 419 C364 374 373 331 367 290Z" fill="url(#atlasBookRightPaper)" stroke="#c4d8f0" stroke-width=".85"/>

          <g clip-path="url(#atlasBookLeftClip)">
            <path d="M144 243 C218 221 296 241 362 291" fill="none" stroke="#fff" stroke-width="2" opacity=".94"/>
            <g class="atlas-book-page-ink" fill="none" stroke="#7797c0" stroke-linecap="round" opacity=".24" stroke-width="1.25">__LEFT_INK__</g>
            <path d="M163 258 Q190 253 222 259" fill="none" stroke="#5c86bc" stroke-width="3.2" stroke-linecap="round" opacity=".3"/>
            <path d="M231 261 Q246 264 260 269" fill="none" stroke="#93b2d7" stroke-width="2.8" stroke-linecap="round" opacity=".28"/>
            <path d="M127 340 C187 330 265 357 329 393" fill="none" stroke="#adc7e7" stroke-width=".7" opacity=".4"/>
          </g>

          <g fill="none" stroke="#809fc5" stroke-width="1.1" stroke-linecap="round" opacity=".19">
            <path d="M393 382 C455 349 535 319 617 324"/>
            <path d="M394 393 C462 357 539 333 620 335"/>
          </g>
          <path d="M365 297 C427 232 520 210 611 230 L632 310 C532 301 434 364 356 419 C380 353 373 324 365 297Z" fill="url(#atlasBookLeafUnder)"/>

          <g class="atlas-book-leaf">
            <path d="M367 290 C435 224 521 202 604 219 L626 291 C535 283 434 354 354 419 C369 357 375 322 367 290Z" fill="url(#atlasBookRaisedPaper)" stroke="#c3d8f2" stroke-width=".85"/>
            <path d="M368 289 C433 224 518 203 603 219" fill="none" stroke="#fff" stroke-width="2.1" opacity=".9"/>
            <path d="M354 419 C434 354 535 283 626 291 L627 294 C535 286 438 356 354 420Z" fill="#a7c6ed" opacity=".8"/>
            <path d="M390 276 C448 232 516 219 582 229" fill="none" stroke="#9bb9de" stroke-width=".8" opacity=".28"/>
            <g class="atlas-book-page-diagram" fill="none" stroke="#8eafd7" stroke-width="1" opacity=".45">
              <path d="M446 292 474 266 510 270 542 247M474 266 476 294 510 270 540 277"/>
              <path d="M433 315 Q504 278 568 280" stroke-dasharray="2 4" opacity=".6"/>
              <circle cx="446" cy="292" r="2.3" fill="#f8fbff"/>
              <circle cx="474" cy="266" r="3.5" fill="#f8fbff"/>
              <circle cx="510" cy="270" r="2.6" fill="#f8fbff"/>
              <circle cx="542" cy="247" r="2.3" fill="#f8fbff"/>
              <circle cx="476" cy="294" r="2.1" fill="#f8fbff"/>
              <circle cx="540" cy="277" r="2.1" fill="#f8fbff"/>
            </g>
            <path d="M406 336 C435 317 463 302 489 292" fill="none" stroke="#94afd1" stroke-width="1.1" stroke-linecap="round" opacity=".28"/>
          </g>

          <path class="atlas-book-spine" d="M365 288 C375 326 368 370 354 420 L347 416 C364 367 368 325 359 285Z" fill="url(#atlasBookFold)"/>
          <path d="M367 291 C373 333 364 380 354 420" fill="none" stroke="#fff" stroke-width="1.35" opacity=".84"/>
          <path d="M359 416 C367 427 374 438 393 449 L380 450 377 460 C367 449 361 435 354 421Z" fill="url(#atlasBookRibbon)"/>
          <path d="M360 420 Q365 438 379 451" fill="none" stroke="#b9daff" stroke-width=".75" opacity=".7"/>
          <path class="atlas-book-page-edge" d="M106 356 C182 341 279 376 353 419 M356 419 C451 367 548 322 647 338" fill="none" stroke="#9bbce4" stroke-width=".9" opacity=".75"/>
        </g></g>
      </svg>
    """.replace("__PAPER_EDGES__", paper_edges).replace("__LEFT_INK__", left_ink).replace("__NODES__", nodes)
