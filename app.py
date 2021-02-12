# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
import logging
import sys
from logging import Formatter, FileHandler
from datetime import datetime
import babel
from flask import (
    render_template,
    request,
    flash,
    redirect,
    url_for,
    Response
)
from flask_moment import Moment
from sqlalchemy import func

from forms import *
from models import app, db, Venue, Artist, Show

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app.config.from_object('config')
moment = Moment(app)
db.init_app(app)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(value, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    venue_all = Venue.query.order_by(Venue.created_at.desc()).limit(10)
    artist_all = Artist.query.order_by(Artist.created_at.desc()).limit(10)
    return render_template('pages/home.html', venues=venue_all, artists=artist_all)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    areas = db.session.query(Venue.city, Venue.state, func.count(Venue.id)).group_by(Venue.city, Venue.state).all()
    venue_all = Venue.query.all()
    num_upcoming_shows = db.session.query(Show.venue_id, func.count(Show.id).label("count")).filter(
        Show.start_time > datetime.now()).group_by(Show.venue_id).all()
    return render_template('pages/venues.html', areas=areas, venues=venue_all, num_upcoming_shows=num_upcoming_shows);


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    location = db.session.query(Venue).filter(func.concat(Venue.city, ', ', Venue.state) == search_term).all()
    search_result = db.session.query(Venue).filter(Venue.name.ilike(f'%{search_term}%')).all()
    num_upcoming_shows = db.session.query(Show.venue_id, func.count(Show.id).label("count")).filter(
        Show.start_time > datetime.now()).group_by(Show.venue_id).all()
    if len(location) > 0:
        response = location
    else:
        response = search_result
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''), num_upcoming_shows=num_upcoming_shows)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue:
        return render_template('errors/404.html')
    upcoming = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id).filter(
        Show.start_time > datetime.now()).all()
    past = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id).filter(
        Show.start_time < datetime.now()).all()
    return render_template('pages/show_venue.html', venue=venue, upcoming_shows=upcoming, past_shows=past)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    try:
        if 'seeking_talent' in request.form:
            seeking_talent = True
        else:
            seeking_talent = False
        venue = Venue(name=request.form['name'], city=request.form['city'], state=request.form['state'],
                      address=request.form['address'], phone=request.form['phone'],
                      genres=request.form.getlist('genres'),
                      facebook_link=request.form['facebook_link'], image_link=request.form['image_link'],
                      website=request.form['website'],
                      seeking_talent=seeking_talent, seeking_description=request.form['seeking_description'])
        db.session.add(venue)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash(request.form['name'] + ' could not be listed due to An error occurred.')
    if not error:
        flash('Venue ' + request.form['name'] + ' successfully listed!')
    return redirect('/')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    error = False
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash(f'An error occurred. Venue {venue_id} could not be deleted.')
    if not error:
        flash(f'Venue {venue_id} was successfully deleted.')
    return redirect('/')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = db.session.query(Artist).all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    location = db.session.query(Artist).filter(func.concat(Artist.city, ', ', Artist.state) == search_term).all()
    search_result = db.session.query(Artist).filter(Artist.name.ilike(f'%{search_term}%')).all()
    if len(location) > 0:
        response = location
    else:
        response = search_result
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = db.session.query(Artist).get(artist_id)
    if not artist:
        return render_template('errors/404.html')
    past_shows = db.session.query(Show).join(Venue).filter(Show.artist_id == artist_id).filter(
        Show.start_time < datetime.now()).all()
    upcoming_shows = db.session.query(Show).join(Venue).filter(Show.artist_id == artist_id).filter(
        Show.start_time > datetime.now()).all()
    return render_template('pages/show_artist.html', artist=artist, past_shows=past_shows,
                           upcoming_shows=upcoming_shows)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    if artist:
        form.name.data = artist.name
        form.city.data = artist.city
        form.state.data = artist.state
        form.phone.data = artist.phone
        form.genres.data = artist.genres
        form.facebook_link.data = artist.facebook_link
        form.image_link.data = artist.image_link
        form.website.data = artist.website
        form.seeking_venue.data = artist.seeking_venue
        form.seeking_description.data = artist.seeking_description
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    error = False
    artist = Artist.query.get(artist_id)

    try:
        artist.name = request.form['name']
        artist.city = request.form['city']
        artist.state = request.form['state']
        artist.phone = request.form['phone']
        artist.genres = request.form.getlist('genres')
        artist.image_link = request.form['image_link']
        artist.facebook_link = request.form['facebook_link']
        artist.website = request.form['website']
        if 'seeking_venue' in request.form:
            artist.seeking_venue = True
        else:
            artist.seeking_venue = False
        artist.seeking_description = request.form['seeking_description']

        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist could not be changed.')
    if not error:
        flash('Artist was successfully updated!')

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)

    if venue:
        form.name.data = venue.name
        form.city.data = venue.city
        form.state.data = venue.state
        form.phone.data = venue.phone
        form.address.data = venue.address
        form.genres.data = venue.genres
        form.facebook_link.data = venue.facebook_link
        form.image_link.data = venue.image_link
        form.website.data = venue.website
        form.seeking_talent.data = venue.seeking_talent
        form.seeking_description.data = venue.seeking_description
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    error = False
    venue = Venue.query.get(venue_id)

    try:
        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.address = request.form['address']
        venue.phone = request.form['phone']
        venue.genres = request.form.getlist('genres')
        venue.image_link = request.form['image_link']
        venue.facebook_link = request.form['facebook_link']
        venue.website = request.form['website']
        if 'seeking_talent' in request.form:
            venue.seeking_talent = True
        else:
            venue.seeking_talent = False
        venue.seeking_description = request.form['seeking_description']

        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash(f'An error occurred. Venue could not be changed.')
    if not error:
        flash(f'Venue was successfully updated!')
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False
    try:
        if 'seeking_venue' in request.form:
            seeking_venue = True
        else:
            seeking_venue = False
        artist = Artist(name=request.form['name'], city=request.form['city'], state=request.form['state'],
                        phone=request.form['phone'], genres=request.form.getlist('genres'),
                        facebook_link=request.form['facebook_link'],
                        image_link=request.form['image_link'], website=request.form['website'],
                        seeking_venue=seeking_venue,
                        seeking_description=request.form['seeking_description'])
        db.session.add(artist)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('Artist ' + request.form['name'] + ' could not be listed.')
    if not error:
        flash('Artist ' + request.form['name'] + ' successfully listed!')
    return redirect('/')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    all_shows = db.session.query(Show).join(Artist).join(Venue).all()
    return render_template('pages/shows.html', shows=all_shows)


@app.route('/show/search', methods=['POST'])
def search_shows():
    search_terms = request.form.get('search_term', '')
    all_shows_data = db.session.query(Show).join(Artist).join(Venue).filter(
        (Venue.name.ilike(f'%{search_terms}%')) | (Artist.name.ilike(f'%{search_terms}%'))).all()
    return render_template('pages/show.html', results=all_shows_data,
                           search_term=request.form.get('search_term', ''))


@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    try:
        artist_id = request.form['artist_id']
        venue_id = request.form['venue_id']
        start_time = request.form['start_time']
        show_availability = db.session.query(Show).filter(
            (Show.artist_id == artist_id) & (Show.venue_id == venue_id) & (Show.start_time == start_time)).all()
        if len(show_availability) > 0:
            error = True
            flash('Already Booked Before')
        else:
            show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
            db.session.add(show)
            db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Show could not be listed.')
    if not error:
        flash('Show was successfully listed')
    return redirect('/shows')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


@app.errorhandler(401)
def custom_401(error):
    return Response('Unauthorized Page', 401,
                    {'WWW-Authenticate': 'Basic realm="Login Required"'})


@app.errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403


@app.errorhandler(422)
def not_processable(error):
    return render_template('errors/403.html'), 422


@app.errorhandler(405)
def invalid_method(error):
    return render_template('errors/405.html'), 405


@app.errorhandler(409)
def duplicate_resource(error):
    return render_template('errors/409.html'), 409


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
