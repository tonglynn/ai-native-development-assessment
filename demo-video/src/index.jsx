import { registerRoot, Composition } from "remotion";
import { AttestFilm, FILM_FRAMES } from "./Film";
registerRoot(() => <Composition id="AttestFilm" component={AttestFilm} durationInFrames={FILM_FRAMES} fps={30} width={1920} height={1080} />);
